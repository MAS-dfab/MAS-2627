import json
import os
import sys
import time

import serial   # pyserial, installed in the mas26_t1 conda env

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from print_class_02 import PrintPath

# Reads data/out_printpoints.json (made by design.ghx) and sends it to the robot with compas_urc
# https://github.com/MAS-dfab/compas_urc  (pip install git+https://github.com/MAS-dfab/compas_urc.git)
# Units: mm, mm/s

HERE = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(HERE, "config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints_weijiun_nonplanar.json")   # = the save panel in design_weijiun.gh

SEND = False        # False = test run: only prints what would be sent, no robot or Arduino needed. True = real run

ACCEL = 100.0       # mm/s2
START_PAUSE = 0.2   # s, wait after the extruder turns on, so the material starts flowing before the robot moves
# START_PAUSE = 1.0 (original pause value)

# ---- extruder speed over serial (pyserial). For a new project, change these. ----
SERIAL_PORT = "COM3"    # TODO: check in Arduino IDE -> Tools -> Port. Close the Serial Monitor first, it blocks the port
BAUD_RATE = 115200      # must match Serial.begin(...) in the Arduino sketch
LINE_END = "\n"         # same as the line ending chosen in the Arduino Serial Monitor
BOOT_TIME = 3.0         # s, the Mega restarts when the port opens (and forgets aspeed), so wait before sending
SPEED_MIN = 0.0         # allowed aspeed values: the script stops before anything moves if one is outside
SPEED_MAX = 10.0

# (A) sent once before the print: aspeed channel -> value
START_SPEEDS = {
    0: 7.0,   # aspeed 0, picked by DO3 (extruder_index 3, the main body)
    1: 1.0,   # aspeed 1, picked by DO2 (extruder_index 2, the thin lines)
}
# (B) changes during the print: layer_index -> {channel: value},
# sent when the robot reaches the first point of that layer. Empty = no changes.
# e.g. {10: {0: 6.0}} prints from layer 10 on with aspeed 0 at 6
LAYER_SPEEDS = {}
# ---------------------------------------------------------------------------------

# TODO: the tool (extruder) as a frame relative to the flange, in mm
# TODO: Fill in the digital output numbers for the extruder on/off, and the logic (True/False) for on/off
TOOL_FRAME = Frame(
    [-57.08, 44.54, 189.5],
    [1, 0, 0],
    [0, 1, 0]
    )
# wiring on this robot (tested on the pendant, 2026-11-11): DO0 heater off (never used here), DO1 extruder stop,
# DO2 -> aspeed 1, DO3 -> aspeed 0 (the other way round than the L02 slides), DO2+DO3 = retract
# extruder_index -> (DO1, DO2, DO3). The speeds themselves are sent over serial (START_SPEEDS, LAYER_SPEEDS above)
EXTRUDER_STATES = {
    1: (True,  False, False),   # off
    2: (False, True,  False),   # DO2 = aspeed 1: class 2, the thin lines
    3: (False, False, True),    # DO3 = aspeed 0: class 3, the main body
}

# TODO: Fill in the digital output numbers for the extruder on/off, and the logic (True/False) for on/off
def set_extruder(ur, urc, index):
    d1, d2, d3 = EXTRUDER_STATES[index]
    # go through "off" first: never passes through the retract code (DO2+DO3),
    # and lets firmware that only reads the speed on switch-on pick up the change
    ur.send(urc.SetDigital(1, True))
    ur.send(urc.SetDigital(2, False))
    ur.send(urc.SetDigital(3, False))
    if index != 1:
        ur.send(urc.SetDigital(1, d1))
        ur.send(urc.SetDigital(2, d2))
        ur.send(urc.SetDigital(3, d3))


def check_speeds():
    # catch typos before the robot or the extruder does anything
    for speeds in [START_SPEEDS] + list(LAYER_SPEEDS.values()):
        for channel, value in speeds.items():
            if channel not in START_SPEEDS:
                # if channel input is outside of the 2 channels defined, send error to user and stop the program
                raise ValueError(f"aspeed channel {channel} is not in START_SPEEDS")
            if not SPEED_MIN <= value <= SPEED_MAX:
                # ensures that the robot never moves with a speed that the extruder cannot handle
                raise ValueError(f"aspeed {channel} {value} is outside {SPEED_MIN} to {SPEED_MAX}")


def open_arduino():
    if not SEND:
        print(f"test: would open {SERIAL_PORT} at {BAUD_RATE} baud, then wait {BOOT_TIME} s")
        return TestArduino()
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(BOOT_TIME)   # opening the port restarts the Mega
    arduino.reset_input_buffer()
    return arduino


def set_speeds(arduino, speeds):
    # same text you would type in the Serial Monitor, e.g. "aspeed 0 7"
    for channel, value in speeds.items():
        command = f"aspeed {channel} {value:g}"
        arduino.write((command + LINE_END).encode())
        print("serial:", command)
    arduino.flush()


# ---- test run (SEND = False): stand-ins with the same methods as the real robot and Arduino ----
class TestArduino(object):
    def write(self, data):
        print("  test: bytes to the Arduino:", data)   # shows the exact text and line ending

    def flush(self):
        pass

    def close(self):
        print("test: serial port closed")


class TestFuture(object):
    # the real one completes when the robot has done the move; here it is done at once
    def __init__(self, move):
        self.move = move

    def result(self, timeout=None):
        print(f"test: robot reaches move {self.move}")
        return True


class TestRobot(object):
    def __init__(self, urc):
        self.urc = urc
        self.moves = 0
        self.last = None

    def send(self, instruction):
        if isinstance(instruction, self.urc.MoveToFrame):
            self.moves += 1
            self.last = instruction
            if self.moves == 1:
                self.print_move("first")
        elif isinstance(instruction, self.urc.SetDigital):
            io, value = instruction.params[:2]
            print(f"after move {self.moves}: DO{int(io)} {bool(value)}")
        elif isinstance(instruction, self.urc.WaitTime):
            print(f"after move {self.moves}: wait {instruction.params[0]:g} s")
        else:
            print(f"after move {self.moves}: {type(instruction).__name__}")
        return TestFuture(self.moves)

    def print_move(self, name):
        # params of a move: x, y, z in m, rotation, speed in m/s
        x, y, z = [round(v * 1000, 1) for v in self.last.params[:3]]
        print(f"{name} move ({self.moves}), robot base: x {x}, y {y}, z {z} mm, speed {self.last.params[6] * 1000:g} mm/s")

    def wait_all(self, timeout=None):
        pass

    def close(self):
        self.print_move("last")
        print(f"test: {self.moves} moves, robot disconnected")

    def abort(self, digital_outputs=None):
        print("test: abort, outputs set to", digital_outputs)
# ---------------------------------------------------------------------------------


def wait_for(urc, wait):
    # wait in short steps: on Windows a wait without timeout ignores Ctrl+C
    while True:
        try:
            return wait(0.5)
        except urc.TimeoutException:
            pass


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def load_printpath():
    with open(PRINT_FILE, "r") as f:
        return PrintPath.from_dict(json.load(f))


def wobj_to_robot_base(printpath, wobj):
    # same idea as rhino_to_robotbase in 04_RoboticBricks
    transformation = Transformation.from_frame_to_frame(Frame.worldXY(), wobj)
    return [printpoint.frame.transformed(transformation) for printpoint in printpath.printpoints]


def main():
    check_speeds()

    config = load_config()
    # Reads the configuration file of the workobject, defined by Frame(origin, xaxis, xypoint)

    wobj = Frame.from_points(Point(*config["wobj"]["origin"]), Point(*config["wobj"]["xaxis"]), Point(*config["wobj"]["xypoint"]))
    # Conversion of config file information into Compas.Geometry.Frame object

    printpath = load_printpath()   # safety points are already in the JSON (added in design.ghx)
    # Transform from the workobject frame to the robot base frame, so the robot can move to the points

    frames = wobj_to_robot_base(printpath, wobj)
    print(config["group"], printpath)

    # a segment prints only if both of its printpoints have the extruder on
    points = printpath.printpoints
    extruding_after = [points[i].is_extruder_on and points[i + 1].is_extruder_on for i in range(len(points) - 1)] + [False]

    import compas_urc as urc
    # Imported here rather than at the top of this script

    if SEND:
        ur = urc.URClient(config["robot_ip"])
        # Reads robot IP address from config file
        ur.connect()
        # Sets up a connection to the robot
    else:
        print(f"test: would connect to the robot at {config['robot_ip']}")
        ur = TestRobot(urc)

    arduino = None
    try:
        # TODO: ur.send(urc.SetTool(EXTRUDER))
        ur.send(urc.SetTool(urc.Tool(TOOL_FRAME, name = "extruder")))
        # extruder off before the first move: the outputs may still be on from a manual test on the pendant
        set_extruder(ur, urc, 1)
        wait_for(urc, ur.wait_all)   # extruder is off before the Mega restarts

        # (A) the Mega restarts when the port opens and forgets aspeed, so send the speeds every run
        arduino = open_arduino()
        set_speeds(arduino, START_SPEEDS)

        current = 1
        layer_changes = []   # (B) (future of the move, speeds to send when the robot gets there)
        for i, (printpoint, frame) in enumerate(zip(points, frames)):
            future = ur.send(urc.MoveToFrame(frame, printpoint.speed, ACCEL, printpoint.blend_radius, urc.Motion.PROCESS))
            first_of_layer = i == 0 or printpoint.layer_index != points[i - 1].layer_index
            if first_of_layer and printpoint.layer_index in LAYER_SPEEDS:
                layer_changes.append((future, LAYER_SPEEDS[printpoint.layer_index]))
            # the next segment (point i -> i+1) uses the extruder speed of the point it moves to,
            # the same point whose robot speed it uses
            wanted = points[i + 1].extruder_index if extruding_after[i] else 1
            if wanted != current:
                set_extruder(ur, urc, wanted)
                if current in (None, 1) and wanted != 1:
                    ur.send(urc.WaitTime(START_PAUSE))   # let material start flowing
                current = wanted
        set_extruder(ur, urc, 1)

        # (B) all moves are queued and the robot keeps moving. Here we only wait until it
        # reaches each layer and then send the new speed (a few ms late, at the start of the blend)
        for future, speeds in layer_changes:
            wait_for(urc, future.result)
            set_speeds(arduino, speeds)

        wait_for(urc, ur.wait_all)
        ur.close()
    except (KeyboardInterrupt, Exception) as error:
        ur.abort({1: True, 2: False, 3: False})   # stop the robot and switch the extruder off
        print("aborted:", error)
    finally:
        if arduino is not None:
            arduino.close()


if __name__ == "__main__":
    # This script is meant to be run from the command line, not from Rhino/Grasshopper
    # If this is disabled, the script can be run from Rhino/Grasshoppper, but the robot will not be able to connect to the computer.
    main()
