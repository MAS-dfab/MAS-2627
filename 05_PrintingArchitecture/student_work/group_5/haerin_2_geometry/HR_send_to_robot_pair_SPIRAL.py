"""Send the continuous wavy spiral from data/out_printpoints.json.

WARNING: With SEND=True this script connects to the physical robot and
starts commanding motion. Use only with a trained operator and checked path.

Coordinates: mm. Robot speed: mm/s. Acceleration: mm/s^2.
"""

import json
import os
import sys

from compas.geometry import Frame, Point, Transformation


# This file belongs in 05_PrintingArchitecture/student_work/group_5/haerin_2_geometry/
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "..", "src"))
sys.path.insert(0, SRC_DIR)

from print_class import PrintPath


# Default: inspect the plan without connecting to a robot.
SEND = False  # Set to False for a dry run without robot connection.
# All body ASPEED assignments come from the GH JSON.

CONFIG_FILE = os.path.join(HERE, "config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints.json")

# Keep the original measured settings unless a tutor confirms changes.
ACCEL = 100.0
START_PAUSE = 1.0
TOOL_FRAME = Frame([23.47, -44.37, 147.5], [1, 0, 0], [0, 1, 0])

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
    meta = data.get("workflow_meta", {})
    if (meta.get("schema") != "sketch_continuous_spiral_v1"
            or meta.get("tool_orientation") != "spiral_radial_tangent_normal"
            or meta.get("continuous_body") is not True):
        raise ValueError("Save from design_viz_pair_spiral_print GH first. This sender is for the continuous spiral only.")
    printpath = PrintPath.from_dict(data)
    printpath.workflow_meta = meta
    points = printpath.printpoints
    if len(points) < 4 or points[0].is_extruder_on or points[-1].is_extruder_on:
        raise ValueError("Missing extruder-OFF approach/retract endpoints")
    import math
    for point in points:
        values = list(point.frame.point) + list(point.frame.xaxis) + list(point.frame.yaxis)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Nonfinite frame data")
        if point.is_extruder_on and point.frame.point.z < 0:
            raise ValueError("Printing path below work-object Z=0")
    top = max(p.frame.point.z for p in points if p.is_extruder_on)
    if points[0].frame.point.z <= top or points[-1].frame.point.z <= top:
        raise ValueError("Approach/retract points must clear the entire part")

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
    """Continuous MoveP through base/spiral/rim; ignore body layer labels.
    MoveL/zero blend at initial approach, priming exit, body entry and finish only.
    """
    import math
    points = printpath.printpoints
    modes = printpath.aspeed_modes
    if len(points) < 2 or len(points) != len(frames) or len(points) != len(modes):
        raise ValueError("Point/frame/mode count mismatch")

    # Each entry describes the segment FROM point i TO point i+1.
    printing = [
        points[i].is_extruder_on and points[i+1].is_extruder_on
        and modes[i] is not None
        for i in range(len(points)-1)
    ] + [False]

    actions, count = [], 0
    extruding, selected = False, None
    for i, (point, frame) in enumerate(zip(points, frames)):
        if not math.isfinite(point.speed) or not 0 < point.speed <= 50:
            raise ValueError("Robot speed must be finite and within 0..50 mm/s")
        if not math.isfinite(point.blend_radius) or point.blend_radius < 0:
            raise ValueError("Blend must be finite and nonnegative")

        # Stop only at print-block entry/exit and IO boundaries, not turn labels.
        # Only a print-to-print interior target can use MoveP blending.
        incoming_print = i > 0 and printing[i-1]
        outgoing_print = printing[i]
        continuous = (incoming_print and outgoing_print and modes[i-1] == modes[i])
        blend, motion = 0.0, "linear"
        if continuous:
            incoming = point.frame.point.distance_to_point(points[i-1].frame.point)
            outgoing = point.frame.point.distance_to_point(points[i+1].frame.point)
            blend = min(point.blend_radius, incoming/2.1, outgoing/2.1)
            if blend > 0:
                motion = "process"
        actions.append(("move", frame, point.speed, blend, motion))

        if outgoing_print:
            mode = modes[i]
            if mode != selected:
                actions.append(("speed", mode))
                selected = mode
            if not extruding:
                actions.append(("extruder", True))
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

    # A failed connect has not reached our motion/IO command loop.
    # Do NOT upload an abort script to the robot in response to connect failure.
    try:
        ur.connect()
    except BaseException:
        print("Connection failed before tool, motion or extruder commands were sent.")
        print("No abort script or extruder command was sent by this handler.")
        # Release the partially opened PC-side RTDE connection only.
        rtde = getattr(ur, "rtde", None)
        if rtde is not None:
            try:
                rtde.close()
                ur.rtde = None
            except Exception as error:
                print("RTDE cleanup error:", error)
        raise

    try:
        ur.send(urc.SetTool(urc.Tool(TOOL_FRAME, name="extruder")))
        extruder_off(ur, urc)
        for action in actions:
            kind = action[0]
            if kind == "move":
                _, frame, speed, blend, motion = action
                motion_type = urc.Motion.PROCESS if motion == "process" else urc.Motion.LINEAR
                ur.send(urc.MoveToFrame(frame, speed, ACCEL, blend, motion_type))
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
        # Installed compas_urc supports setting IOs in the abort script itself.
        # The normal instruction queue is unusable after abort(), so do not send
        # another queued extruder_off command afterwards.
        try:
            ur.abort(digital_outputs={DO_EXTRUDER_OFF: True,
                                      DO_SPEED_0: False, DO_SPEED_1: False})
        except Exception as error:
            print("Abort/IO command could not be confirmed:", error)
        raise
    finally:
        try:
            ur.close(timeout=2.0)
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
    meta = printpath.workflow_meta
    print("Source JSON:", PRINT_FILE)
    print("Tool orientation:", meta["tool_orientation"])
    print("WORK-OBJECT printed bounds (mm):", meta["body_bounds"])
    print("Same-angle layer rise min/max (mm):", meta["min_same_angle_rise"], meta["max_same_angle_rise"])
    print("Max tool tilt / max target-to-target Frame change (deg):", meta["max_tool_tilt_deg"], meta["max_frame_step_deg"])
    print("Priming bounds in work object (mm):", meta["priming_bounds"])
    moves = [a for a in actions if a[0] == "move"]
    positive = [a[3] for a in moves if a[4] == "process"]
    print("Motion: Continuous MoveP through body turns and final rim; MoveL at print-block boundaries.")
    print("MoveP targets:", len(positive), "| MoveL targets:", len(moves)-len(positive))
    print("MoveP blend min/max (mm):", (min(positive), max(positive)) if positive else None)
    print("Body turn labels do NOT switch extrusion or motion mode. Positive local blend cap retained.")
    base_min = [min(getattr(f.point,k) for f in frames) for k in ("x","y","z")]
    base_max = [max(getattr(f.point,k) for f in frames) for k in ("x","y","z")]
    print("ROBOT-BASE full target bounds incl. approach/retract (mm):", base_min, base_max)
    seconds = sum(printpath.printpoints[i].frame.point.distance_to_point(printpath.printpoints[i-1].frame.point)
                  / printpath.printpoints[i].speed for i in range(1,len(printpath.printpoints)))
    print("Ideal travel time excluding acceleration (min):", round(seconds/60.,2))
    print("Priming start wait only. Prime -> inward travel OFF -> continuous base/spiral/rim ON -> retract OFF.")

    print('ASPEED selections follow GH metadata; body is ASPEED1. Check Arduino feed value.')
    print('First 18 selections:', [a[1] for a in actions if a[0] == 'speed'][:18])
    if not SEND:
        print('DRY RUN: no robot connection or digital outputs sent.')
        return
    print('LIVE MODE: connecting to the robot and sending motions NOW.')
    run_robot(actions, config["robot_ip"])


if __name__ == "__main__":
    main()


