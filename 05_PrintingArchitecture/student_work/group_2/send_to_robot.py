import json
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
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints.json")

ACCEL = 100.0       # mm/s2
START_PAUSE = 1.0   # s, wait after the extruder turns on, so the material starts flowing before the robot moves

# TODO: the tool (extruder) as a frame relative to the flange, in mm
# TODO: Fill in the digital output numbers for the extruder on/off, and the logic (True/False) for on/off
TOOL_FRAME = Frame(
    [0.0, 0.0, 190.0], 
    [1, 0, 0], 
    [0, 1, 0]
    )
# EXTRUDER = urc.Tool(TOOL_FRAME, name = "extruder")

# TODO: Fill in the digital output numbers for the extruder on/off, and the logic (True/False) for on/off
def extruder_on(ur, urc):
    # Set 1 to False, set 2/3 to True
    pass  # ur.send(urc.SetDigital(?, ?))

def extruder_off(ur, urc):
    # Set 1 to True, set 2/3 to False
    pass  # ur.send(urc.SetDigital(?, ?))


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

    ur = urc.URClient(config["robot_ip"])
    ur.connect()
    try:
        # TODO: ur.send(urc.SetTool(EXTRUDER))
        extruding = False
        for i, (printpoint, frame) in enumerate(zip(points, frames)):
            ur.send(urc.MoveToFrame(frame, printpoint.speed, ACCEL, printpoint.blend_radius, urc.Motion.LINEAR))
            if extruding_after[i] != extruding:   # the robot switches the IO between the moves
                extruding = extruding_after[i]
                if extruding:
                    extruder_on(ur, urc)
                    ur.send(urc.WaitTime(START_PAUSE))   # the robot stops at this point while it waits
                else:
                    extruder_off(ur, urc)
        extruder_off(ur, urc)
        ur.wait_all()
        ur.close()
    except KeyboardInterrupt:
        ur.abort()   # TODO: pass digital_outputs to switch the extruder off
        print("aborted")


if __name__ == "__main__":
    # This script is meant to be run from the command line, not from Rhino/Grasshopper
    # If this is disabled, the script can be run from Rhino/Grasshoppper, but the robot will not be able to connect to the computer.
    main()
