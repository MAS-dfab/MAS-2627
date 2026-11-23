"""Send the dwell-aware bead network from data/out_bead_network.json.

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
SEND = True  # Set to False for a dry run without robot connection.
# All body ASPEED assignments come from the GH JSON.

CONFIG_FILE = os.path.join(HERE, "config.json")
PRINT_FILE = os.path.join(HERE, "data", "out_bead_network.json")

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
    if meta.get('schema')!='pair_bead_network_v1' or meta.get('tool_orientation')!='fixed_course_minusX_plusY':
        raise ValueError('Save from nonplanar_pair_bead_network.gh first. This sender requires bead dwell metadata.')
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
    dwells=[]
    for index,(item,point) in enumerate(zip(data['printpoints'],points)):
        dwell=float(item.get('dwell_sec',0.))
        if not math.isfinite(dwell) or not 0<=dwell<=5:raise ValueError('Dwell must be 0..5 seconds')
        if dwell>0 and (item.get('dwell_aspeed_mode')!=1 or not point.is_extruder_on):raise ValueError('Invalid bead dwell at point '+str(index))
        if dwell>0 and point.blend_radius!=0:raise ValueError('Bead centre must have zero blend')
        dwells.append(dwell)
    printpath.dwell_seconds=dwells
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


def build_plan(printpath,frames):
    """Pure offline planner. Arrive at bead centre exactly, select ASPEED1, dwell.
    Outgoing segment modes remain None=travel / 0=thin / 1=solid.
    """
    import math
    points=printpath.printpoints;modes=printpath.aspeed_modes;dwells=printpath.dwell_seconds
    if not len(points)==len(frames)==len(modes)==len(dwells):raise ValueError('Metadata length mismatch')
    printing=[points[i].is_extruder_on and points[i+1].is_extruder_on and modes[i] is not None for i in range(len(points)-1)]+[False]
    actions=[];extruding=False;selected=None;count=0
    for i,(p,frame) in enumerate(zip(points,frames)):
        if not math.isfinite(p.speed) or not 0<p.speed<=50:raise ValueError('Invalid speed')
        if not math.isfinite(p.blend_radius) or p.blend_radius<0:raise ValueError('Invalid blend')
        incoming=i>0 and printing[i-1];outgoing=printing[i]
        blend=0.
        if incoming and outgoing and modes[i-1]==modes[i] and dwells[i]==0:
            blend=min(p.blend_radius,p.frame.point.distance_to_point(points[i-1].frame.point)/2.1,p.frame.point.distance_to_point(points[i+1].frame.point)/2.1)
        actions.append(('move',frame,p.speed,blend,'linear'))
        if dwells[i]>0:
            if selected!=1:actions.append(('speed',1));selected=1
            if not extruding:actions.append(('extruder',True));extruding=True
            actions.append(('wait',dwells[i]))
        if outgoing:
            mode=modes[i]
            if mode!=selected:actions.append(('speed',mode));selected=mode
            if not extruding:
                actions.append(('extruder',True));extruding=True
                if p.layer_index==0:actions.append(('wait',START_PAUSE))
            count+=1
        elif extruding:
            actions.append(('extruder',False));extruding=False;selected=None
    actions.append(('extruder',False));return actions,count

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

    moves=[a for a in actions if a[0]=='move']
    print('Source:',PRINT_FILE)
    print('Moves:',len(moves),'Bead dwells:',sum(v>0 for v in printpath.dwell_seconds))
    print('Total bead hold seconds:',sum(printpath.dwell_seconds))
    print('MoveL with local blending; exact stop at bead centres; ASPEED1 dwell then ASPEED0 bridges.')
    print('REQUIRED Arduino presets: ASPEED0=0, ASPEED1=2. This sender selects digital presets; it does not configure Arduino values.')
    print('Tool frame:',TOOL_FRAME)
    print('Work object:',config.get('wobj'))
    print('Fixed vertical nozzle. Original nonplanar XYZ retained. Reach/nozzle clearance and actual bead geometry require operator validation.')
    if not SEND:
        print('DRY RUN: no robot connection or digital outputs sent.')
        return
    print('LIVE MODE: connecting to the robot and sending motions NOW.')
    run_robot(actions, config["robot_ip"])


if __name__ == "__main__":
    main()


