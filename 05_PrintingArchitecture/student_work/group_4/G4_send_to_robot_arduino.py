# region --- IMPORTS ---
import json
import os
import sys

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation
import compas_urc as urc

# endregion

# region --- SYS FILE LOCATION ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from G4_print_class import PrintPath
from G4_arduino import Arduino

# Reads the printpoints JSON (made by design.ghx) and sends it to the robot with compas_urc
# https://github.com/MAS-dfab/compas_urc  (pip install git+https://github.com/MAS-dfab/compas_urc.git)
# Units: mm, mm/s
HERE = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(HERE, "data", "G4_config.json")
PRINT_FILE = os.path.join(HERE, "data", "G4_combined_textured.json")

# endregion

# region --- PARAMETERS ---
ACCEL = 1000        # mm/s2
START_PAUSE = 0.1   # s, wait after the extruder turns on, so the material starts flowing before the robot moves
ASPEED_STOP = 5     # robot DO: Extrusion Speed STOP (in Arduino)
ASPEED_0 = 6        # robot DO: selects Arduino preset "aspeed 0"
ASPEED_1 = 7        # robot DO: selects Arduino preset "aspeed 1"

# Arduino (serial, same commands as in the Arduino IDE). The serial monitor must be CLOSED.
ARDUINO_PORT = "COM4"
HEATER_TEMP = 220           # "heater 1 220"
TEMP_TOLERANCE = 3.0        # degrees: start printing when the temperature stays within this ...
TEMP_STABLE_TIME = 10.0     # ... for this many seconds

# Extrusion speed values (aspeed_value of each printpoint, from the printpath component).
# The two Arduino presets are used in turns: while the robot prints with one, the script sets the
# next value in the other one over serial; the robot switches preset (DO 6 / DO 7) exactly where the
# value changes. So the change is synchronised with the motion.
ASPEED_STEP = 0.1           # values are rounded to this step; a smaller change is not sent
MIN_CHANGE_DISTANCE = 10.0  # mm of path between two value changes (gives the script time to react)
FALLBACK_VALUES = {0: 3.0, 1: 5.0}  # per aspeed_io, for JSON files without aspeed_value

TOOL_FRAME = Frame([-12.74, 44.73, 144.19], [1, 0, 0], [0, 1, 0]) # TCP
EXTRUDER = urc.Tool(TOOL_FRAME, name = "extruder")

# endregion

# region --- FUNCTIONS ---
def select_preset(ur, preset):
    """Extruder on with Arduino preset 0 (DO 6) or 1 (DO 7). Returns the future of the last command:
    it is done when the robot has executed the switch."""
    ur.send(urc.SetDigital(ASPEED_STOP, False))
    ur.send(urc.SetDigital(ASPEED_0, preset == 0))
    return ur.send(urc.SetDigital(ASPEED_1, preset == 1))

def extruder_off(ur):
    # 5--- true
    # 6/7--- false
    ur.send(urc.SetDigital(ASPEED_STOP, True))
    ur.send(urc.SetDigital(ASPEED_0, False))
    ur.send(urc.SetDigital(ASPEED_1, False))

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def load_printpath():
    with open(PRINT_FILE, "r") as f:
        return PrintPath.from_dict(json.load(f))

def wobj_to_robot_base(printpath, wobj):
    transformation = Transformation.from_frame_to_frame(Frame.worldXY(), wobj)
    return [printpoint.frame.transformed(transformation) for printpoint in printpath.printpoints]

def plan_value_changes(points):
    """Where the extrusion value changes, and which preset carries it.
    Segment i goes from point i to point i + 1; it prints if both points have the extruder on,
    with the value of point i + 1 (the point it moves to).
    Returns: printing (bool per segment) and changes: list of (segment index, preset, value).
    A new change starts every time printing starts, and when the value moved at least ASPEED_STEP
    and at least MIN_CHANGE_DISTANCE mm of path were printed since the last change."""
    printing = [points[i].is_extruder_on and points[i + 1].is_extruder_on for i in range(len(points) - 1)]
    changes = []
    current, preset, distance = None, 1, 0.0
    for i, prints in enumerate(printing):
        if not prints:
            current = None
            continue
        target = points[i + 1]
        value = target.aspeed_value
        if value is None:                                  # older JSON: fixed value per aspeed_io
            value = FALLBACK_VALUES.get(target.aspeed_io, FALLBACK_VALUES[0])
        value = round(value / ASPEED_STEP) * ASPEED_STEP
        if current is None or (abs(value - current) >= ASPEED_STEP - 1e-9 and distance >= MIN_CHANGE_DISTANCE):
            preset = 1 - preset                            # use the presets in turns: 0, 1, 0, 1, ...
            changes.append((i, preset, value))
            current, distance = value, 0.0
        distance += points[i].frame.point.distance_to_point(target.frame.point)
    return printing, changes

#endregion

# region --- MAIN ---
def main():
    config = load_config()
    wobj = Frame.from_points(Point(*config["wobj"]["origin"]), Point(*config["wobj"]["xaxis"]), Point(*config["wobj"]["xypoint"]))

    printpath = load_printpath()   # safety points are already in the JSON (added in design.ghx)

    # Transform from the workobject frame to the robot base frame, so the robot can move to the points
    frames = wobj_to_robot_base(printpath, wobj)
    print(config["group"], printpath)

    points = printpath.printpoints
    printing, changes = plan_value_changes(points)
    change_at = {segment: k for k, (segment, _, _) in enumerate(changes)}
    print("{} value changes, values {:.2f} to {:.2f}".format(
        len(changes), min(c[2] for c in changes), max(c[2] for c in changes)))

    # ===== Arduino: heater, first two values =====
    arduino = Arduino(ARDUINO_PORT)              # the Mega restarts here (heater off): set it again
    arduino.set_heater(HEATER_TEMP)
    arduino.wait_for_temperature(HEATER_TEMP, TEMP_TOLERANCE, TEMP_STABLE_TIME)
    for _, preset, value in changes[:2]:         # the first two changes: one in each preset
        arduino.set_aspeed(preset, value)

    ur = urc.URClient(config["robot_ip"])
    ur.connect()

    try:
        # ===== Queue the whole print (streamed to the robot in the background) =====
        ur.send(urc.SetTool(EXTRUDER))
        switches = []                            # future of each preset switch, in order
        extruding = False
        for i, (printpoint, frame) in enumerate(zip(points, frames)):
            ur.send(urc.MoveToFrame(frame, printpoint.speed, ACCEL, printpoint.blend_radius, urc.Motion.PROCESS))
            if i in change_at:                   # the robot switches the preset between the moves
                _, preset, _ = changes[change_at[i]]
                switches.append(select_preset(ur, preset))
                if not extruding:
                    ur.send(urc.WaitTime(START_PAUSE))   # the robot stops at this point while it waits
                extruding = True
            elif extruding and i < len(printing) and not printing[i]:
                extruder_off(ur)
                extruding = False
        extruder_off(ur)

        # ===== While it prints: refill the free preset with the next value =====
        # When the robot has executed switch k, the other preset is free until switch k + 1 uses it.
        late = 0
        for k in range(1, len(changes) - 1):
            switches[k].result()                 # wait until the robot reached change k
            _, preset, value = changes[k + 1]
            if getattr(switches[k + 1], "done", lambda: False):   # the robot was faster than the serial update
                late += 1
            arduino.set_aspeed(preset, value)
            if k % 50 == 0:
                print("value change {} / {}".format(k, len(changes)))

        ur.wait_all()
        ur.close()
        print("done{}".format(", {} value updates arrived late".format(late) if late else ""))
    except KeyboardInterrupt: # ctrl + C
        ur.abort(digital_outputs={ASPEED_STOP: True, ASPEED_0: False, ASPEED_1: False}) # pass digital_outputs to switch the extruder off
        print("aborted")
    finally:
        arduino.close()                          # closing does not restart the Arduino: the heater stays at HEATER_TEMP

if __name__ == "__main__":
    main()

# endregion