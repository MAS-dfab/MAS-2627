"""Send a printing path directly to a UR robot with alternating extrusion speeds.

WARNING: With SEND=True this script connects to the physical robot and
starts commanding motion. Use only with a trained operator and checked path.

Coordinates: mm. Robot speed: mm/s. Acceleration: mm/s^2.
"""

import json
import os
import sys

from compas.geometry import Frame, Point, Transformation


# This file belongs in 05_PrintingArchitecture/student_work/group_5/haerin/
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "..", "src"))
sys.path.insert(0, SRC_DIR)

from print_class import PrintPath


# Default: inspect the plan without connecting to a robot.
SEND = True
# All body ASPEED assignments come from the GH JSON.

CONFIG_FILE = os.path.join(HERE, "config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints.json")

# Keep the original measured settings unless a tutor confirms changes.
ACCEL = 100.0
START_PAUSE = 1.0
TOOL_FRAME = Frame([-4.54, -42.11, 148.48], [1, 0, 0], [0, 1, 0])

# Based on the class wiring diagram; confirm physical wiring before printing.
DO_EXTRUDER_OFF = 5  # True = OFF, False = ON
DO_SPEED_0 = 6
DO_SPEED_1 = 7
# IMPORTANT: DO6 and DO7 must not both be True (retract signal).


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_printpath():
    with open(PRINT_FILE, "r") as f:
        data = json.load(f)
    printpath = PrintPath.from_dict(data)
    modes = []
    for index, (item, point) in enumerate(zip(data["printpoints"], printpath.printpoints)):
        if point.is_extruder_on and "aspeed_mode" not in item:
            raise ValueError("Missing GH ASPEED metadata at point {}. Resave using Stage 2 GH.".format(index))
        mode = item.get("aspeed_mode")
        if mode is not None and (type(mode) is not int or mode not in (0, 1)):
            raise ValueError("Invalid ASPEED at point {}".format(index))
        modes.append(mode)
    printpath.aspeed_modes = modes
    return printpath


def wobj_to_robot_base(printpath, wobj):
    transformation = Transformation.from_frame_to_frame(Frame.worldXY(), wobj)
    return [point.frame.transformed(transformation) for point in printpath.printpoints]


def extruder_off(ur, urc):
    """Switch off extrusion and both speed-selection outputs."""
    ur.send(urc.SetDigital(DO_EXTRUDER_OFF, True))
    ur.send(urc.SetDigital(DO_SPEED_0, False))
    ur.send(urc.SetDigital(DO_SPEED_1, False))


def extruder_on(ur, urc):
    """Start extrusion; the correct speed must already be selected."""
    ur.send(urc.SetDigital(DO_EXTRUDER_OFF, False))


def select_extruder_speed(ur, urc, mode):
    """Select ASPEED0 or ASPEED1 without ever commanding both outputs ON."""
    if mode not in (0, 1):
        raise ValueError("Extruder speed mode must be 0 or 1")

    # Clear the previous selection before turning on the next one.
    ur.send(urc.SetDigital(DO_SPEED_0, False))
    ur.send(urc.SetDigital(DO_SPEED_1, False))
    ur.send(urc.SetDigital(DO_SPEED_0 if mode == 0 else DO_SPEED_1, True))


def build_plan(printpath, frames):
    """Use GH metadata exactly; no splitting, alternation or body pauses here."""
    import math
    points = printpath.printpoints
    modes = printpath.aspeed_modes
    if len(points) < 2 or len(points) != len(frames) or len(points) != len(modes):
        raise ValueError("Point/frame/mode count mismatch")
    actions, count = [], 0
    extruding, selected = False, None
    for i, (point, frame) in enumerate(zip(points, frames)):
        if not math.isfinite(point.speed) or point.speed <= 0:
            raise ValueError("Robot speed must be finite and positive")
        if point.blend_radius != 0:
            raise ValueError("Set GH blend_radius=0 and save again for this experiment")
        actions.append(("move", frame, point.speed, 0.0))
        mode = modes[i]
        printing_next = (i+1 < len(points) and point.is_extruder_on
                         and points[i+1].is_extruder_on and mode is not None)
        if printing_next:
            if mode != selected:
                actions.append(("speed", mode))
                selected = mode
            if not extruding:
                actions.append(("extruder", True))
                # Preserve only the original priming start pause; none on body.
                if point.layer_index == 0:
                    actions.append(("wait", START_PAUSE))
            extruding = True
            count += 1
        elif extruding:
            actions.append(("extruder", False))
            extruding, selected = False, None
    actions.append(("extruder", False))
    return actions, count


def run_robot(actions, robot_ip):
    import compas_urc as urc

    ur = urc.URClient(robot_ip)
    try:
        ur.connect()
        ur.send(urc.SetTool(urc.Tool(TOOL_FRAME, name="extruder")))

        # Initial state: extruder OFF, speed outputs OFF.
        extruder_off(ur, urc)

        for action in actions:
            kind = action[0]
            if kind == "move":
                _, frame, speed, blend = action
                ur.send(urc.MoveToFrame(frame, speed, ACCEL, blend, urc.Motion.LINEAR))
            elif kind == "speed":
                select_extruder_speed(ur, urc, action[1])
            elif kind == "extruder":
                if action[1]:
                    extruder_on(ur, urc)
                else:
                    extruder_off(ur, urc)
            elif kind == "wait":
                ur.send(urc.WaitTime(action[1]))

        extruder_off(ur, urc)
        ur.wait_all()
    except BaseException:
        # Abort is best-effort. It does NOT replace the physical emergency stop.
        try:
            ur.abort()
        except Exception as error:
            print("Robot abort error:", error)
        try:
            extruder_off(ur, urc)
        except Exception as error:
            print("Extruder OFF command could not be confirmed:", error)
        raise
    finally:
        try:
            ur.close()
        except Exception as error:
            print("Robot close error:", error)


def main():
    config = load_config()
    wobj = Frame.from_points(
        Point(*config["wobj"]["origin"]),
        Point(*config["wobj"]["xaxis"]),
        Point(*config["wobj"]["xypoint"]),
    )

    printpath = load_printpath()
    frames = wobj_to_robot_base(printpath, wobj)
    actions, segment_count = build_plan(printpath, frames)

    print("Group:", config.get("group", "unknown"))
    print("Printing segments:", segment_count)
    print('ASPEED source: GH metadata; no body pauses or point alternation')
    print('First 18 selections:', [a[1] for a in actions if a[0] == 'speed'][:18])
    if not SEND:
        print('DRY RUN: no robot connection or digital outputs sent.')
        return
    print('LIVE MODE: connecting to the robot and sending motions NOW.')
    run_robot(actions, config["robot_ip"])


if __name__ == "__main__":
    main()


