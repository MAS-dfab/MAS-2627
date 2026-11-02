"""
Stage-by-stage line drawing animation of one temple with its base
and the neighbouring dominos (temple_design.temple_scene).

    stages, tangent = temple_design.temple_scene(...)
    states = build_states(stages)
    render(states[step], canvas, tangent)
    export_frames(states, tangent, folder)

One animation step = one build stage. Deterministic: the same curve
and parameters always give the same frames.
"""

import math
import os

from brick_element import Brick
from wall_animation import (
    Camera, Fit, SvgCanvas, PngCanvas,
    axon_polygons, box_corners, paint_order, _xyz, _copy,
)

TITLE = "Combining Temple and Base"

INK = "#444444"          # text
LINE = "#9a9a9a"         # bricks already placed
LINE_NEW = "#555555"     # bricks added in this stage
FILL_NEW = "#ededed"
GREY = "#a8a8a8"         # panel labels
LIGHT = "#e0e0e0"        # separator


def dims(brick):
    if brick.type == "standing":
        return (Brick.HEIGHT, Brick.WIDTH, Brick.LENGTH)
    return (Brick.LENGTH, Brick.WIDTH, Brick.HEIGHT)


# ==========================================
# 1. STATES
# ==========================================

def build_states(stages):
    """intro (empty) + one state per stage + final."""

    every = [b for title, bricks in stages for b in bricks]
    params = getattr(stages, "params", {})
    total = len(stages)

    def state(n, title, placed, current):
        return {"title": title, "placed": list(placed), "current": list(current),
                "every": every, "params": params, "stage": n, "stages": total}

    states = [state(0, "START", [], [])]
    placed = []
    for n, (title, bricks) in enumerate(stages):
        states.append(state(n + 1, title, placed, bricks))
        placed.extend(bricks)
    states.append(state(total, "FINAL", placed, []))
    return states


# ==========================================
# 2. FORMULAS / PARAMETERS / COUNTS
# ==========================================

def _f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def formulas(state):
    """Two formula lines for the stage, values from the actual bricks."""

    p = state["params"]
    L, W, H = Brick.LENGTH, Brick.WIDTH, Brick.HEIGHT
    title = state["title"]
    cur = state["current"]
    z0 = p.get("ground_z", 0.0)
    z = (cur[0].frame.point.z - z0) if cur else 0.0
    top_base = 2 * H

    if title == "START":
        return ("brick  L x W x H = %s x %s x %s mm" % (_f(L), _f(W), _f(H)),
                "temple at params[pick_number] = params[%s]" % p.get("pick_number", "?"))

    if title.startswith("TEMPLE BASE"):
        i = int(title.split()[-1]) - 1
        return ("d_x = (L + 1) / 2 = %s mm" % _f((L + 1) / 2.0),
                "keep (i, j) if i %% 2 == j %% 2      z = H/2 + i * H = %s + %d * %s = %s mm"
                % (_f(H / 2), i, _f(H), _f(z)))

    if title == "SIDE BASE":
        return ("param = params[pick_number - 1] = params[%s]" % (p.get("pick_number", 1) - 1),
                "x = +/- d_x = +/- %s mm      z = H/2 = %s mm" % (_f((L + 1) / 2.0), _f(z)))

    if title == "DOMINO":
        pitch = W + p.get("gap", 0)
        return ("pitch = W + gap = %s + %s = %s mm" % (_f(W), _f(p.get("gap", 0)), _f(pitch)),
                "positions = floor(crv_length / pitch) + 1 = floor(%s / %s) + 1 = %d      "
                "on a base: z = base top" % (_f(p.get("crv_length", 0)), _f(pitch),
                                              p.get("count", 0) + 1))

    if title.startswith("STANDING PAIR"):
        k = int(title.split()[-1])
        lap = p.get("lapping", 0)
        return ("d_x = L/2 - lapping + H/2 = %s - %s + %s = %s mm"
                % (_f(L / 2), _f(lap), _f(H / 2), _f(L / 2 - lap + H / 2)),
                "z = top_base + L/2 + (k - 1) * L = %s + %s + %d * %s = %s mm"
                % (_f(top_base), _f(L / 2), k - 1, _f(L), _f(z)))

    if title == "TOP BRICK":
        lay = p.get("layers", 0)
        return ("z = top_base + layers * L + H/2 = %s + %s * %s + %s = %s mm"
                % (_f(top_base), lay, _f(L), _f(H / 2), _f(z)),
                "overlap on each standing brick = lapping = %s mm" % _f(p.get("lapping", 0)))

    # FINAL
    n = {}
    for b in state["placed"]:
        n[b.type] = n.get(b.type, 0) + 1
    return ("   ".join("%s: %d" % (t, n[t]) for t in sorted(n)),
            "total: %d bricks" % len(state["placed"]))


def parameter_lines(state):
    """Rows of (left column, right column)."""
    p = state["params"]
    return [
        ("layers = %s" % p.get("layers", "-"), "lapping = %s mm" % _f(p.get("lapping", 0))),
        ("gap = %s mm" % _f(p.get("gap", 0)), "pick_number = %s" % p.get("pick_number", "-")),
        ("n_domino = %s" % p.get("n_domino", "-"),
         "brick = %s x %s x %s mm" % (_f(Brick.LENGTH), _f(Brick.WIDTH), _f(Brick.HEIGHT))),
    ]


def count_lines(state):
    built = state["placed"] + state["current"]
    lay = sum(1 for b in built if b.type == "laying")
    return [
        "stage  %d / %d" % (state["stage"], state["stages"]),
        "this stage  +%d" % len(state["current"]),
        "placed  %d / %d" % (len(built), len(state["every"])),
        "laying %d   -   standing %d" % (lay, len(built) - lay),
    ]


# ==========================================
# 3. RENDER ONE STATE
# ==========================================

def _top_face(brick):
    corners, _ = box_corners(brick.frame, dims(brick))
    top = sorted(corners, key=lambda p: -p[2])[:4]
    # order the 4 top corners around their centre
    cx = sum(p[0] for p in top) / 4.0
    cy = sum(p[1] for p in top) / 4.0
    top.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    return [(p[0], p[1]) for p in top], max(p[2] for p in corners)


def render(state, canvas, tangent, camera=None, width=1920, height=1080,
           title=TITLE, elev_depth=20.0):
    """elev_depth: only bricks within this distance (mm, along the
    tangent) of the temple are drawn in the elevation."""

    k = width / 1920.0

    def S(v):
        return v * k

    cam = camera or Camera()
    # Elevation perpendicular to the curve: look along the tangent
    elev = Camera(math.degrees(math.atan2(-tangent.y, -tangent.x)), 0.0)

    axon_rect = (S(50), S(80), S(1180), S(790))
    top_rect = (S(1230), S(90), S(1870), S(420))
    elev_rect = (S(1230), S(470), S(1870), S(760))

    # The temple is the last stage (top brick)
    centre = _xyz(state["every"][-1].frame.point)
    t = (tangent.x, tangent.y, tangent.z)

    def in_slice(b):
        p = _xyz(b.frame.point)
        return abs(sum((p[i] - centre[i]) * t[i] for i in range(3))) <= elev_depth

    # ---- fitting from the final temple, so frames never jump ----
    ext_a, ext_t, ext_e = [], [], []
    for b in state["every"]:
        for poly in axon_polygons(b.frame, cam, dims(b)):
            ext_a.extend(poly)
        if in_slice(b):
            for poly in axon_polygons(b.frame, elev, dims(b)):
                ext_e.extend(poly)
        ext_t.extend(_top_face(b)[0])
    f_a = Fit(ext_a, axon_rect, 0.08)
    f_t = Fit(ext_t, top_rect, 0.1)
    f_e = Fit(ext_e, elev_rect, 0.1)

    # ---- header ----
    canvas.text((width / 2.0, S(42)), title, S(24), INK, anchor="middle")
    canvas.text((S(50), S(80)), "AXONOMETRIC", S(12), GREY)
    canvas.text((S(1230), S(90)), "TOP", S(12), GREY)
    canvas.text((S(1230), S(470)), "ELEVATION (PERPENDICULAR TO CURVE)", S(12), GREY)

    items = [(b, False) for b in state["placed"]] + [(b, True) for b in state["current"]]

    def style(is_new):
        if is_new:
            return dict(stroke=LINE_NEW, width=S(1.8), fill=FILL_NEW, dash=None)
        return dict(stroke=LINE, width=S(1.0), fill="#ffffff", dash=None)

    # ---- axonometric and elevation: painter's algorithm ----
    for view, fit, subset in ((cam, f_a, items),
                              (elev, f_e, [it for it in items if in_slice(it[0])])):
        order = paint_order([(b.frame, dims(b)) for b, new in subset], view)
        for b, new in (subset[i] for i in order):
            for poly in axon_polygons(b.frame, view, dims(b)):
                canvas.polygon([fit(p) for p in poly], **style(new))

    # ---- top view: lower top faces first ----
    faces = sorted(((_top_face(b), new) for b, new in items), key=lambda f: f[0][1])
    for (poly, z), new in faces:
        canvas.polygon([f_t(p) for p in poly], **style(new))

    # ---- brick type labels: one leader per type in this stage ----
    labelled = set()
    for b in state["current"]:
        if b.type in labelled:
            continue
        labelled.add(b.type)
        a = f_a(cam.project(_xyz(b.frame.point)))
        if len(labelled) == 1:
            _label(canvas, a, b.type, k, -1)
        else:
            _label(canvas, a, b.type, k, +1)

    # ---- counts (bottom left of the axon panel) ----
    for n, line in enumerate(count_lines(state)):
        canvas.text((S(60), S(690) + n * S(24)), line, S(16), INK)

    # ---- caption: stage title + formulas ----
    types = sorted(set(b.type for b in state["current"]))
    canvas.line((S(50), S(812)), (S(1870), S(812)), LIGHT, S(1))
    canvas.text((S(60), S(866)), state["title"], S(22), INK, bold=True)
    if types:
        canvas.text((S(400), S(866)), "type: " + " + ".join(types), S(16), GREY)
    canvas.line((S(60), S(880)), (S(380), S(880)), INK, S(1.2))
    for n, line in enumerate(formulas(state)):
        canvas.text((S(60), S(918) + n * S(28)), line, S(16), INK)

    # ---- parameters (bottom right) ----
    canvas.text((S(1230), S(866)), "PARAMETERS", S(12), GREY)
    for n, (left, right) in enumerate(parameter_lines(state)):
        canvas.text((S(1230), S(900) + n * S(26)), left, S(16), INK)
        canvas.text((S(1430), S(900) + n * S(26)), right, S(16), INK)

    return canvas


def _label(canvas, p, label, k, side):
    """Leader from the brick centre out to the left (-1) or right (+1)."""
    q = (p[0] + side * 190 * k, p[1] - 70 * k)
    canvas.dot(p, 2.5 * k, INK)
    canvas.line(p, q, INK, 1.0 * k)
    canvas.line(q, (q[0] + side * 14 * k, q[1]), INK, 1.0 * k)
    canvas.text((q[0] + side * 18 * k, q[1] + 5 * k), label, 15 * k, INK,
                anchor="start" if side > 0 else "end")


# ==========================================
# 4. EXPORT FRAME SEQUENCE
# ==========================================

def export_frames(states, tangent, folder, fmt="png", width=1920, height=1080,
                  frames_per_stage=18, hold_end=36, camera=None, title=TITLE):
    """frame_00000.png ... ; each stage is held frames_per_stage frames."""

    if not os.path.isdir(folder):
        os.makedirs(folder)

    # remove frames of a previous export (sequence may now be shorter)
    for name in os.listdir(folder):
        if name.startswith("frame_") and name.endswith("." + fmt):
            os.remove(os.path.join(folder, name))

    Canvas = PngCanvas if fmt == "png" else SvgCanvas
    paths = []

    for n, state in enumerate(states):
        repeat = frames_per_stage + (hold_end if n == len(states) - 1 else 0)
        first = os.path.join(folder, "frame_%05d.%s" % (len(paths), fmt))
        canvas = Canvas(width, height)
        render(state, canvas, tangent, camera, width, height, title)
        canvas.save(first)
        paths.append(first)
        for _ in range(repeat - 1):
            path = os.path.join(folder, "frame_%05d.%s" % (len(paths), fmt))
            _copy(first, path)
            paths.append(path)

    return paths
