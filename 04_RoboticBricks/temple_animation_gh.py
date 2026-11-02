# r : compas
# venv: mas-2627
"""
"Temple animation" component in (video)brick_to_robot.ghx (Python 3 Script).

INPUTS
    crv, layers, lapping, pick_number, gap   same sources as the temple "Brick wall" component
    n_domino     dominos on each side of the temple
    step         0 .. n_steps-1, one build stage per step
    export       True -> write the whole frame sequence
    folder       output folder (default: temple_animation_frames next to the .ghx)
    fmt          "png" (default) or "svg"

OUTPUTS
    n_steps      number of animation states
    placed       boxes built in earlier stages
    current      boxes added in this stage
    sheet        2D line drawing of this step (XY plane, 0.1 scale)
    sheet_dashed dashed lines of the drawing
    caption      stage title of this step
    paths        exported frame files
"""

from compas_rhino.devtools import DevTools
DevTools.ensure_path()

import os
import sys
import importlib

import Rhino.Geometry as rg
from compas_rhino.conversions import curve_to_compas

FOLDER = os.path.dirname(ghenv.Component.OnPingDocument().FilePath or "")
if FOLDER and FOLDER not in sys.path:
    sys.path.append(FOLDER)

import wall_animation
import temple_design
import temple_animation
importlib.reload(wall_animation)
importlib.reload(temple_design)
importlib.reload(temple_animation)

dims = temple_animation.dims


def to_box(brick):
    f = brick.frame
    L, W, H = dims(brick)
    plane = rg.Plane(rg.Point3d(f.point.x, f.point.y, f.point.z),
                     rg.Vector3d(f.xaxis.x, f.xaxis.y, f.xaxis.z),
                     rg.Vector3d(f.yaxis.x, f.yaxis.y, f.yaxis.z))
    return rg.Box(plane, rg.Interval(-L / 2, L / 2),
                  rg.Interval(-W / 2, W / 2), rg.Interval(-H / 2, H / 2))


stages, tangent = temple_design.temple_scene(
    curve_to_compas(crv),
    gap=float(gap),
    pick_number=int(pick_number),
    lapping=float(lapping),
    layers=int(layers),
    n_domino=6 if n_domino is None else int(n_domino))

states = temple_animation.build_states(stages)
n_steps = len(states)

s = 0 if step is None else max(0, min(int(step), n_steps - 1))
state = states[s]

placed = [to_box(b) for b in state["placed"]]
current = [to_box(b) for b in state["current"]]
caption = state["title"]

canvas = wall_animation.RhinoCanvas(1920, 1080, scale=0.1)
temple_animation.render(state, canvas, tangent)
sheet, sheet_dashed = canvas.curves, canvas.dashed

paths = []
if export:
    out = folder or os.path.join(FOLDER, "temple_animation_frames")
    paths = temple_animation.export_frames(states, tangent, out, fmt=fmt or "png")
    print("wrote %d frames to %s" % (len(paths), out))
