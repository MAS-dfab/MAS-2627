import bisect
import json
import math
import os
import sys

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from print_class import PrintPath

# Reads data/out_printpoints.json (made by design.ghx) and sends it to the robot with compas_urc
# https://github.com/MAS-dfab/compas_urc  (pip install git+https://github.com/MAS-dfab/compas_urc.git)
# Units: mm, mm/s

HERE = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(HERE, "config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints_weijiun.json")

ACCEL = 100.0       # mm/s2
START_PAUSE = 1.0   # s, wait after the extruder turns on, so the material starts flowing before the robot moves

# TODO: the tool (extruder) as a frame relative to the flange, in mm
# TODO: Fill in the digital output numbers for the extruder on/off, and the logic (True/False) for on/off
TOOL_FRAME = Frame(
    [-57.08, 44.54, 189.5], 
    [1, 0, 0], 
    [0, 1, 0]
    )
# EXTRUDER = urc.Tool(TOOL_FRAME, name = "extruder")

# TODO: Fill in the digital output numbers for the extruder on/off, and the logic (True/False) for on/off
def extruder_on(ur, urc):
    ur.send(urc.SetDigital(1, False))
    ur.send(urc.SetDigital(2, True))
    # ur.send(urc.SetDigital(3, True))
    # pass  # ur.send(urc.SetDigital(?, ?))

def extruder_off(ur, urc):
    ur.send(urc.SetDigital(1, True))
    ur.send(urc.SetDigital(2, False))
    # ur.send(urc.SetDigital(3, False))
    # pass  # ur.send(urc.SetDigital(?, ?))


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


def show_progress(ur, move_ids, points, frames, width=30):
    """One line in the terminal: bar, %, point, layer, time left (from path length / speed)."""
    reached = bisect.bisect_right(move_ids, ur.executed)   # printpoints the robot has reached
    i = max(reached - 1, 0)
    # time for each segment = length / speed of the point it moves to
    seconds = [math.dist(frames[k].point, frames[k + 1].point) / points[k + 1].speed for k in range(len(frames) - 1)]
    done, total = sum(seconds[:i]), sum(seconds)
    fraction = done / total if total else 1.0
    left = int(total - done)
    bar = "#" * int(width * fraction) + "-" * (width - int(width * fraction))
    print(f"\r[{bar}] {fraction * 100:5.1f}%  point {reached}/{len(points)}  "
          f"layer {points[i].layer_index + 1}/{points[-1].layer_index + 1}  left {left // 60:02d}:{left % 60:02d}",
          end="", flush=True)


def main():
    
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

    ur = urc.URClient(config["robot_ip"], frequency=50)   # 50 Hz instead of 125: the PC keeps up, the controller does not drop RTDE
    # Reads robot IP address from config file
    ur.connect()
    # Sets up a connection to the robot

    try:
        # TODO: ur.send(urc.SetTool(EXTRUDER))
        ur.send(urc.SetTool(urc.Tool(TOOL_FRAME, name = "extruder")))
        extruding = False
        move_ids = []   # sequence id of the move to each printpoint, for the progress bar
        for i, (printpoint, frame) in enumerate(zip(points, frames)):
            future = ur.send(urc.MoveToFrame(frame, printpoint.speed, ACCEL, printpoint.blend_radius, urc.Motion.PROCESS))
            move_ids.append(future.instruction.sequence_id)
            if extruding_after[i] != extruding:   # the robot switches the IO between the moves
                extruding = extruding_after[i]
                if extruding:
                    extruder_on(ur, urc)
                    ur.send(urc.WaitTime(START_PAUSE))   # the robot stops at this point while it waits
                else:
                    extruder_off(ur, urc)
        extruder_off(ur, urc)
        # wait in short steps: on Windows a wait without timeout ignores Ctrl+C
        # every step also redraws the progress bar
        while True:
            try:
                ur.wait_all(timeout=0.5)
                break
            except urc.TimeoutException:
                show_progress(ur, move_ids, points, frames)
        show_progress(ur, move_ids, points, frames)
        print()
        ur.close()
    except (KeyboardInterrupt, Exception) as error:
        ur.abort({1: True, 2: False, 3: False})   # stop the robot and switch the extruder off
        print("aborted:", error) 


if __name__ == "__main__":
    # This script is meant to be run from the command line, not from Rhino/Grasshopper
    # If this is disabled, the script can be run from Rhino/Grasshoppper, but the robot will not be able to connect to the computer.
    main()
