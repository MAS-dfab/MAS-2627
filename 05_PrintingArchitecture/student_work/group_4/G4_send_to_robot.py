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

# Reads data/out_printpoints.json (made by design.ghx) and sends it to the robot with compas_urc
# https://github.com/MAS-dfab/compas_urc  (pip install git+https://github.com/MAS-dfab/compas_urc.git)
# Units: mm, mm/s
HERE = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(HERE, "data", "G4_config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints_ZH_flipping4.json")

# endregion

# region --- PARAMETERS ---
ACCEL = 1000        # mm/s2
START_PAUSE = 0.1   # s, wait after the extruder turns on, so the material starts flowing before the robot moves
ASPEED_STOP = 5     # I/O of Extrusion Speed STOP (in Arduino)
ASPEED_0 = 6        # I/O of Extrusion Speed (ASPEED 0 in Arduino)
ASPEED_1 = 7        # I/O of Extrusion Speed (ASPEED 1 in Arduino)

TOOL_FRAME = Frame([-12.74, 44.73, 144.19], [1, 0, 0], [0, 1, 0]) # TCP
EXTRUDER = urc.Tool(TOOL_FRAME, name = "extruder")

# endregion

# region --- FUNCTIONS --- 
def extruder_on(ur):
    # 5---false
    # 6/7--- true
    ur.send(urc.SetDigital(ASPEED_STOP, False))
    ur.send(urc.SetDigital(ASPEED_0, True))
    ur.send(urc.SetDigital(ASPEED_1, False))

def extruder_on_2(ur):
    # 5---false
    # 6/7--- true
    ur.send(urc.SetDigital(ASPEED_STOP, False))
    ur.send(urc.SetDigital(ASPEED_0, False))
    ur.send(urc.SetDigital(ASPEED_1, True))

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

#endregion

# region --- MAIN ---
def main():
    config = load_config()
    wobj = Frame.from_points(Point(*config["wobj"]["origin"]), Point(*config["wobj"]["xaxis"]), Point(*config["wobj"]["xypoint"]))

    printpath = load_printpath()   # safety points are already in the JSON (added in design.ghx)

    # Transform from the workobject frame to the robot base frame, so the robot can move to the points
    frames = wobj_to_robot_base(printpath, wobj)
    print(config["group"], printpath)

    # a segment prints only if both of its printpoints have the extruder on
    points = printpath.printpoints
    # extruding_after = [points[i].is_extruder_on and points[i + 1].is_extruder_on for i in range(len(points) - 1)] + [False]
    extruding_after = [
        points[i].aspeed_io
        if (
            points[i].is_extruder_on
            and points[i + 1].is_extruder_on
            # and points[i].aspeed_io == points[i + 1].aspeed_io
        )
        else None
        for i in range(len(points) - 1)
    ] + [None]

    ur = urc.URClient(config["robot_ip"])
    ur.connect()

    try:
        ur.send(urc.SetTool(EXTRUDER))
        extruding = False
        for i, (printpoint, frame) in enumerate(zip(points, frames)):
            ur.send(urc.MoveToFrame(frame, printpoint.speed, ACCEL, printpoint.blend_radius, urc.Motion.LINEAR))
            if extruding_after[i] != extruding:          # the robot switches the IO between the moves
                previous_extruding = extruding_after[i]
                extruding = extruding_after[i]
                if extruding is None:
                    extruder_off(ur)
                elif extruding == 0:
                    extruder_on(ur)
                    if previous_extruding is None:
                        ur.send(urc.WaitTime(START_PAUSE))   # the robot stops at this point while it waits
                elif extruding == 1:
                    extruder_on_2(ur)
                    if previous_extruding is None:
                        ur.send(urc.WaitTime(START_PAUSE))   # the robot stops at this point while it waits
        extruder_off(ur)
        ur.wait_all()
        ur.close()
    except KeyboardInterrupt: # ctrl + C
        ur.abort(digital_outputs={ASPEED_STOP: True, ASPEED_0: False, ASPEED_1: False}) # pass digital_outputs to switch the extruder off
        print("aborted")

if __name__ == "__main__":
    main()

# endregion