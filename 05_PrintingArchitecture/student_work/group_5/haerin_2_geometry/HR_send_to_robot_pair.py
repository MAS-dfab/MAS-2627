"""Send fixed or tilted sketch Frames from data/out_printpoints.json.

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
SEND = True
# All body ASPEED assignments come from the GH JSON.

CONFIG_FILE = os.path.join(HERE, "config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_printpoints.json")

# Keep the original measured settings unless a tutor confirms changes.
ACCEL = 100.0
START_PAUSE = 1.0
TOOL_FRAME = Frame([23.47, -44.37, 148.48], [1, 0, 0], [0, 1, 0])

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
    supported = {
        "sketch_nonplanar_fixed_priming_v1": "fixed_course_minusX_plusY",
        "sketch_nonplanar_tilted_tool_v1": "local_layer_radial_tangent_normal",
    }
    expected = supported.get(meta.get("schema"))
    if expected is None or meta.get("tool_orientation") != expected:
        raise ValueError("Unsupported path. Save from the updated fixed or tilted GH first.")
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
        if not math.isfinite(point.blend_radius) or point.blend_radius < 0:
            raise ValueError("Blend must be finite and nonnegative")
        effective_blend = point.blend_radius
        # Stop at travel boundaries. Apply the same local blend cap to BOTH modes.
        if (i == 0 or i == len(points)-1 or not point.is_extruder_on
                or not points[i-1].is_extruder_on or not points[i+1].is_extruder_on):
            effective_blend = 0.0
        else:
            incoming = point.frame.point.distance_to_point(points[i-1].frame.point)
            outgoing = point.frame.point.distance_to_point(points[i+1].frame.point)
            effective_blend = min(effective_blend, incoming/2.1, outgoing/2.1)
        actions.append(("move", frame, point.speed, effective_blend))
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
    print("Effective blend: requested JSON blend, capped by adjacent lengths; zero at travel boundaries.")
    base_min = [min(getattr(f.point,k) for f in frames) for k in ("x","y","z")]
    base_max = [max(getattr(f.point,k) for f in frames) for k in ("x","y","z")]
    print("ROBOT-BASE full target bounds incl. approach/retract (mm):", base_min, base_max)
    seconds = sum(printpath.printpoints[i].frame.point.distance_to_point(printpath.printpoints[i-1].frame.point)
                  / printpath.printpoints[i].speed for i in range(1,len(printpath.printpoints)))
    print("Ideal travel time excluding acceleration (min):", round(seconds/60.,2))
    print("Priming ASPEED1 (original 1 s start wait) -> inward travel OFF -> body ASPEED1 -> retract OFF.")

    print('ASPEED1 constant; check the Arduino ASPEED1 feed value before LIVE mode.')
    print('First 18 selections:', [a[1] for a in actions if a[0] == 'speed'][:18])
    if not SEND:
        print('DRY RUN: no robot connection or digital outputs sent.')
        return
    print('LIVE MODE: connecting to the robot and sending motions NOW.')
    run_robot(actions, config["robot_ip"])


if __name__ == "__main__":
    main()


