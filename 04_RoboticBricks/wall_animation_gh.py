#! python3
"""
Paste into a Grasshopper "Python 3 Script" component (Rhino 8).

INPUTS  (Type hint)
    crv              Curve
    max_layers       int     (5)
    min_layers       int     (0)
    gap              float   (1.0)
    num_peaks        int     (2)
    min_peak_layers  int     (optional)
    min_connected    int     (optional)
    base_extension   int     (optional)
    step             int     -> Number Slider 0..n_steps-1 (animate it)
    show_rejected    bool    (True)
    azimuth          float   (-60)  axon camera
    elevation        float   (30)
    export           bool    -> Button: writes the whole frame sequence
    folder           str     output folder for frames
    fmt              str     "png" or "svg"

OUTPUTS
    n_steps          number of animation states
    placed           Boxes already in the wall
    current          Box placed / rejected / removed in this step
    top_pts          exposed top frame points so far
    sheet            2D line drawing of this step (XY plane, 0.1 scale)
    sheet_dashed     dashed lines of the 2D drawing
    caption          text of this step
    paths            exported frame files
"""

import os
import sys
import importlib

import Rhino.Geometry as rg

FOLDER = os.path.dirname(ghenv.Component.OnPingDocument().FilePath or "")
if FOLDER and FOLDER not in sys.path:
    sys.path.append(FOLDER)

import slope_design
import wall_animation
importlib.reload(slope_design)
importlib.reload(wall_animation)

L, W, H = slope_design.BRICK_LENGTH, slope_design.BRICK_WIDTH, slope_design.BRICK_HEIGHT


def to_box(frame):
    plane = rg.Plane(
        rg.Point3d(frame.point.x, frame.point.y, frame.point.z),
        rg.Vector3d(frame.xaxis.x, frame.xaxis.y, frame.xaxis.z),
        rg.Vector3d(frame.yaxis.x, frame.yaxis.y, frame.yaxis.z))
    return rg.Box(plane, rg.Interval(-L / 2, L / 2),
                  rg.Interval(-W / 2, W / 2), rg.Interval(-H / 2, H / 2))


def opt(v, default=None):
    return default if v is None else v


# ---------- run the wall function with a trace ----------
trace = []
slope_design.generate_sloped_wall(
    crv,
    max_layers=opt(max_layers, 5),
    min_layers=opt(min_layers, 0),
    gap=opt(gap, 1.0),
    num_peaks=opt(num_peaks, 2),
    min_peak_layers=min_peak_layers,
    min_connected_bricks=min_connected,
    base_extension=base_extension,
    trace=trace)

states = wall_animation.build_states(trace, show_rejected=opt(show_rejected, True))
n_steps = len(states)
camera = wall_animation.Camera(opt(azimuth, -60.0), opt(elevation, 30.0))

s = max(0, min(int(opt(step, n_steps - 1)), n_steps - 1))
state = states[s]

# ---------- 3D preview ----------
placed = [to_box(f) for (key, (f, d)) in state["placed"]
          if not (key == state["key"] and state["kind"] == "place")]
ev = state["event"]
current = to_box(ev["frame"]) if ev and state["kind"] != "top_frame" else None
top_pts = [rg.Point3d(f.point.x, f.point.y, f.point.z) for f in state["tops"]]

# ---------- 2D sheet preview (same drawing as the exported frame) ----------
canvas = wall_animation.RhinoCanvas(1920, 1080, scale=0.1)
wall_animation.render(state, canvas, camera=camera)
sheet, sheet_dashed = canvas.curves, canvas.dashed
caption = "\n".join(t for p, t in canvas.texts)

# ---------- export frame sequence ----------
paths = []
if export:
    out = folder or os.path.join(FOLDER, "wall_animation_frames")
    paths = wall_animation.export_frames(states, out, fmt=opt(fmt, "png"), camera=camera)
    print("wrote %d frames to %s" % (len(paths), out))
