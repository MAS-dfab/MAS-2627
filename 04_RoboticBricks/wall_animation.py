"""
Step-by-step line drawing animation of the bonded wall algorithm
in slope_design.py.

    trace = []
    slope_design.generate_sloped_wall(crv, ..., trace=trace)
    states = build_states(trace)
    render(states[step], canvas)          # one frame
    export_frames(states, folder)         # PNG / SVG sequence

Every state is computed from the trace only, so the animation is
fully deterministic: same curve + parameters -> same frames.
"""

import math
import os

from slope_design import BRICK_LENGTH, BRICK_WIDTH, BRICK_HEIGHT


# ==========================================
# 1. TEXT FOR EACH ALGORITHM STAGE
# ==========================================

STAGES = {
    "intro": (
        "RUNNING BOND CANDIDATES",
        "distance = L/2 + i * pitch + layer * pitch/2",
        "Every layer is shifted by half a pitch.",
    ),
    "place": (
        "RUNNING BOND PLACEMENT",
        "target_height >= layer + 1  and  support(i, i+1)  ->  place",
        "Layer > 0 needs bricks i and i+1 below.",
    ),
    "reject_height": (
        "RUNNING BOND PLACEMENT",
        "target_height < layer + 1  ->  skip",
        "The height profile is lower than this layer.",
    ),
    "reject_support": (
        "RUNNING BOND PLACEMENT",
        "not (i in below and i+1 in below)  ->  skip",
        "A brick can only sit on two bricks.",
    ),
    "remove_isolated": (
        "REMOVE ISOLATED GROUPS",
        "len(group) < min_connected_bricks  ->  remove",
        "Short base groups are unstable.",
    ),
    "trim_base": (
        "TRIM BASE BRICKS",
        "keep base i, i+1 under layer 2  (+/- base_extension)",
        "Base bricks that support nothing are removed.",
    ),
    "top_frame": (
        "EXPOSED TOP FRAMES",
        "not (i in above or i-1 in above)  ->  top frame",
        "Uncovered top faces become support frames.",
    ),
    "final": (
        "FINAL WALL",
        "bricks per layer",
        "",
    ),
}


# ==========================================
# 2. BUILD ANIMATION STATES FROM THE TRACE
# ==========================================

def build_states(trace, show_rejected=True, show_top_frames=True):
    """One state per algorithm event (plus intro and final)."""

    distances = {}
    for e in trace:
        if e["distance"] is not None:
            distances[(e["layer"], e["i"])] = e["distance"]

    # Every brick that ever appears, so the drawing never rescales
    extent = []
    for e in trace:
        if e["kind"] in ("place", "reject_height", "reject_support"):
            extent.append((e["frame"], e["distance"]))

    placed = {}          # (layer, i) -> (frame, distance), insertion = order
    tops = []
    counts = {"placed": 0, "rejected": 0, "removed": 0, "tops": 0}

    def snapshot(kind, event=None):
        key = None if event is None else (event["layer"], event["i"])
        return {
            "kind": kind,
            "event": event,
            "key": key,
            "distance": distances.get(key),
            "placed": list(placed.items()),
            "tops": list(tops),
            "counts": dict(counts),
            "extent": extent,
        }

    states = [snapshot("intro")]

    for e in trace:

        kind = e["kind"]
        key = (e["layer"], e["i"])

        if kind == "place":
            placed[key] = (e["frame"], e["distance"])
            counts["placed"] += 1

        elif kind in ("reject_height", "reject_support"):
            counts["rejected"] += 1
            if not show_rejected:
                continue

        elif kind in ("remove_isolated", "trim_base"):
            # Show it once more (dashed), then it is gone
            counts["removed"] += 1
            states.append(snapshot(kind, e))
            placed.pop(key, None)
            continue

        elif kind == "top_frame":
            if not show_top_frames:
                continue
            tops.append(e["frame"])
            counts["tops"] += 1

        states.append(snapshot(kind, e))

    states.append(snapshot("final"))

    return states


# ==========================================
# 3. BOX GEOMETRY AND PROJECTIONS
# ==========================================

# Faces as corner indices, counter-clockwise from outside,
# with their local normal axis (0=x, 1=y, 2=z) and sign
FACES = [
    ((0, 3, 2, 1), 2, -1),
    ((4, 5, 6, 7), 2, +1),
    ((0, 1, 5, 4), 1, -1),
    ((2, 3, 7, 6), 1, +1),
    ((1, 2, 6, 5), 0, +1),
    ((3, 0, 4, 7), 0, -1),
]


def _xyz(v):
    return (v.x, v.y, v.z)


def box_corners(frame, dims=None):

    o = _xyz(frame.point)
    axes = (_xyz(frame.xaxis), _xyz(frame.yaxis), _xyz(frame.zaxis))
    dims = dims or (BRICK_LENGTH, BRICK_WIDTH, BRICK_HEIGHT)
    half = (dims[0] / 2.0, dims[1] / 2.0, dims[2] / 2.0)

    corners = []
    for sz in (-1, 1):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            s = (sx, sy, sz)
            corners.append(tuple(
                o[k] + sum(s[a] * half[a] * axes[a][k] for a in range(3))
                for k in range(3)
            ))
    return corners, axes


class Camera:
    """Parallel projection. azimuth/elevation in degrees."""

    def __init__(self, azimuth=-60.0, elevation=30.0):
        a = math.radians(azimuth)
        e = math.radians(elevation)
        self.c = (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))
        self.r = (-math.sin(a), math.cos(a), 0.0)
        self.u = (-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e))

    def project(self, p):
        return (_dot(p, self.r), _dot(p, self.u))

    def depth(self, p):
        return _dot(p, self.c)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def axon_polygons(frame, cam, dims=None):
    """Visible faces of one brick, projected."""
    corners, axes = box_corners(frame, dims)
    polys = []
    for idx, axis, sign in FACES:
        n = tuple(sign * c for c in axes[axis])
        if _dot(n, cam.c) > 1e-9:
            polys.append([cam.project(corners[k]) for k in idx])
    return polys


def paint_order(boxes, cam):
    """
    Back-to-front drawing order for non-intersecting boxes.
    boxes: list of (frame, dims). Returns a list of indices.

    Sorting by centre depth fails for long bricks (an upper brick can
    have a farther centre than the lower brick in front of it), so for
    every pair whose projections overlap we find a separating face plane
    and let it decide which box is in front.
    """

    data = []
    for frame, d in boxes:
        corners, axes = box_corners(frame, d)
        o = _xyz(frame.point)
        d = d or (BRICK_LENGTH, BRICK_WIDTH, BRICK_HEIGHT)
        uv = [cam.project(p) for p in corners]
        bbox = (min(p[0] for p in uv), min(p[1] for p in uv),
                max(p[0] for p in uv), max(p[1] for p in uv))
        data.append((corners, axes, o, d, bbox))

    def in_front(a, b):
        """True if box b is in front of box a, False if behind, None if unknown."""
        for s, t, flip in ((a, b, False), (b, a, True)):
            corners_s, axes_s, o_s, d_s, _ = data[s]
            for k in range(3):
                for sign in (1, -1):
                    n = tuple(sign * c for c in axes_s[k])
                    facing = _dot(n, cam.c)
                    if abs(facing) < 1e-9:
                        continue
                    plane = _dot(n, o_s) + d_s[k] / 2.0
                    if all(_dot(n, p) >= plane - 1e-6 for p in data[t][0]):
                        # t lies outside s's face: t is in front if the face looks at us
                        front = facing > 0
                        return front if not flip else not front
        return None

    n = len(data)
    after = [set() for _ in range(n)]       # i -> boxes drawn after i
    indeg = [0] * n
    for i in range(n):
        bi = data[i][4]
        for j in range(i + 1, n):
            bj = data[j][4]
            if bi[2] <= bj[0] or bj[2] <= bi[0] or bi[3] <= bj[1] or bj[3] <= bi[1]:
                continue
            r = in_front(i, j)
            if r is None:
                r = cam.depth(data[j][2]) > cam.depth(data[i][2])
            a, b = (i, j) if r else (j, i)
            if b not in after[a]:
                after[a].add(b)
                indeg[b] += 1

    depth = [cam.depth(dd[2]) for dd in data]
    order, done = [], [False] * n
    for _ in range(n):
        ready = [i for i in range(n) if not done[i] and indeg[i] == 0]
        # a cycle cannot happen for stacked bricks, but never get stuck
        pool = ready or [i for i in range(n) if not done[i]]
        i = min(pool, key=lambda q: depth[q])
        done[i] = True
        order.append(i)
        for j in after[i]:
            indeg[j] -= 1
    return order


def top_polygon(frame, dims=None):
    corners, _ = box_corners(frame, dims)
    return [(corners[k][0], corners[k][1]) for k in (4, 5, 6, 7)]


def elevation_polygon(frame, distance):
    """Unrolled along the curve: x = distance, y = z."""
    z = frame.point.z
    hl, hh = BRICK_LENGTH / 2.0, BRICK_HEIGHT / 2.0
    return [(distance - hl, z - hh), (distance + hl, z - hh),
            (distance + hl, z + hh), (distance - hl, z + hh)]


class Fit:
    """Maps view coordinates into a screen rectangle (y down)."""

    def __init__(self, points, rect, margin=0.06):
        x0, y0, x1, y1 = rect
        xs = [p[0] for p in points] or [0.0]
        ys = [p[1] for p in points] or [0.0]
        w = max(max(xs) - min(xs), 1e-6)
        h = max(max(ys) - min(ys), 1e-6)
        sw = (x1 - x0) * (1 - 2 * margin)
        sh = (y1 - y0) * (1 - 2 * margin)
        self.s = min(sw / w, sh / h)
        self.cx = (min(xs) + max(xs)) / 2.0
        self.cy = (min(ys) + max(ys)) / 2.0
        self.ox = (x0 + x1) / 2.0
        self.oy = (y0 + y1) / 2.0

    def __call__(self, p):
        return (self.ox + (p[0] - self.cx) * self.s,
                self.oy - (p[1] - self.cy) * self.s)


# ==========================================
# 4. DRAWING BACKENDS
# ==========================================

class SvgCanvas:

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.items = []

    def polygon(self, pts, stroke="#000", width=1.0, fill="none", dash=None):
        d = " ".join("%.2f,%.2f" % p for p in pts)
        da = ' stroke-dasharray="%s"' % " ".join(str(x) for x in dash) if dash else ""
        self.items.append(
            '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%.2f"'
            ' stroke-linejoin="round"%s/>' % (d, fill, stroke, width, da))

    def line(self, a, b, stroke="#000", width=1.0, dash=None):
        da = ' stroke-dasharray="%s"' % " ".join(str(x) for x in dash) if dash else ""
        self.items.append(
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s"'
            ' stroke-width="%.2f"%s/>' % (a[0], a[1], b[0], b[1], stroke, width, da))

    def dot(self, p, r, fill="#000"):
        self.items.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                          % (p[0], p[1], r, fill))

    def text(self, p, s, size=14, color="#000", bold=False, anchor="start"):
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.items.append(
            '<text xml:space="preserve" x="%.2f" y="%.2f" font-family="Arial, Helvetica, sans-serif"'
            ' font-size="%.1f" fill="%s" text-anchor="%s"%s>%s</text>'
            % (p[0], p[1], size, color, anchor,
               ' font-weight="bold"' if bold else "", s))

    def save(self, path):
        with open(path, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"'
                    ' viewBox="0 0 %d %d">\n' % (self.w, self.h, self.w, self.h))
            f.write('<rect width="100%" height="100%" fill="#fff"/>\n')
            f.write("\n".join(self.items))
            f.write("\n</svg>\n")


class PngCanvas:
    """System.Drawing backend (Rhino on Windows)."""

    def __init__(self, width, height):
        import clr
        clr.AddReference("System.Drawing")
        import System
        from System import Drawing
        from System.Drawing import Drawing2D, Text, Imaging

        self.S, self.D = System, Drawing
        self.Drawing2D, self.Imaging = Drawing2D, Imaging
        self.bmp = Drawing.Bitmap(int(width), int(height))
        self.g = Drawing.Graphics.FromImage(self.bmp)
        self.g.SmoothingMode = Drawing2D.SmoothingMode.AntiAlias
        self.g.TextRenderingHint = Text.TextRenderingHint.AntiAliasGridFit
        self.g.Clear(Drawing.Color.White)

    def _color(self, c):
        c = c.lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        return self.D.Color.FromArgb(int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

    def _pen(self, stroke, width, dash):
        pen = self.D.Pen(self._color(stroke), float(width))
        pen.LineJoin = self.Drawing2D.LineJoin.Round
        if dash:
            pen.DashPattern = self.S.Array[self.S.Single](
                [max(float(d) / width, 0.1) for d in dash])
        return pen

    def _pts(self, pts):
        return self.S.Array[self.D.PointF]([self.D.PointF(float(x), float(y)) for x, y in pts])

    def polygon(self, pts, stroke="#000", width=1.0, fill="none", dash=None):
        arr = self._pts(pts)
        if fill != "none":
            brush = self.D.SolidBrush(self._color(fill))
            self.g.FillPolygon(brush, arr)
            brush.Dispose()
        pen = self._pen(stroke, width, dash)
        self.g.DrawPolygon(pen, arr)
        pen.Dispose()

    def line(self, a, b, stroke="#000", width=1.0, dash=None):
        pen = self._pen(stroke, width, dash)
        self.g.DrawLine(pen, float(a[0]), float(a[1]), float(b[0]), float(b[1]))
        pen.Dispose()

    def dot(self, p, r, fill="#000"):
        brush = self.D.SolidBrush(self._color(fill))
        self.g.FillEllipse(brush, float(p[0] - r), float(p[1] - r), float(2 * r), float(2 * r))
        brush.Dispose()

    def text(self, p, s, size=14, color="#000", bold=False, anchor="start"):
        style = self.D.FontStyle.Bold if bold else self.D.FontStyle.Regular
        font = self.D.Font("Arial", float(size), style, self.D.GraphicsUnit.Pixel)
        brush = self.D.SolidBrush(self._color(color))
        fmt = self.D.StringFormat()
        fmt.Alignment = {"start": self.D.StringAlignment.Near,
                         "middle": self.D.StringAlignment.Center,
                         "end": self.D.StringAlignment.Far}[anchor]
        fmt.LineAlignment = self.D.StringAlignment.Far   # y is the baseline-ish
        self.g.DrawString(s, font, brush, self.D.PointF(float(p[0]), float(p[1]) + size * 0.2), fmt)
        font.Dispose(); brush.Dispose(); fmt.Dispose()

    def save(self, path):
        self.bmp.Save(path, self.Imaging.ImageFormat.Png)
        self.g.Dispose()
        self.bmp.Dispose()


class RhinoCanvas:
    """Collects the drawing as Rhino curves on the XY plane (preview in GH)."""

    def __init__(self, width, height, scale=0.1):
        import Rhino.Geometry as rg
        self.rg, self.h, self.k = rg, height, scale
        self.curves, self.dashed, self.texts = [], [], []

    def _p(self, p):
        return self.rg.Point3d(p[0] * self.k, (self.h - p[1]) * self.k, 0)

    def polygon(self, pts, stroke="#000", width=1.0, fill="none", dash=None):
        pl = self.rg.Polyline([self._p(p) for p in pts] + [self._p(pts[0])])
        (self.dashed if dash else self.curves).append(pl.ToNurbsCurve())

    def line(self, a, b, stroke="#000", width=1.0, dash=None):
        ln = self.rg.LineCurve(self._p(a), self._p(b))
        (self.dashed if dash else self.curves).append(ln)

    def dot(self, p, r, fill="#000"):
        self.curves.append(self.rg.Circle(self._p(p), r * self.k).ToNurbsCurve())

    def text(self, p, s, size=14, color="#000", bold=False, anchor="start"):
        self.texts.append((self._p(p), s))

    def save(self, path):
        pass


# ==========================================
# 5. RENDER ONE STATE (SHEET LAYOUT)
# ==========================================

INK = "#111"
GREY = "#9a9a9a"
LIGHT = "#d0d0d0"
HILITE = "#e4e4e4"


def render(state, canvas, title="From a Single Brick to Multiple Layers",
           camera=None, width=1920, height=1080):

    k = width / 1920.0
    cam = camera or Camera()

    def S(v):
        return v * k

    axon_rect = (S(50), S(80), S(1180), S(790))
    top_rect = (S(1230), S(90), S(1870), S(420))
    elev_rect = (S(1230), S(470), S(1870), S(760))

    # ---- fitting from every brick that ever appears ----
    ext_axon, ext_top, ext_elev = [], [], []
    for frame, d in state["extent"]:
        for poly in axon_polygons(frame, cam):
            ext_axon.extend(poly)
        ext_top.extend(top_polygon(frame))
        ext_elev.extend(elevation_polygon(frame, d))

    f_axon = Fit(ext_axon, axon_rect, 0.08)
    f_top = Fit(ext_top, top_rect, 0.1)
    f_elev = Fit(ext_elev, elev_rect, 0.1)

    # ---- header and panel labels ----
    canvas.text((width / 2.0, S(42)), title, S(24), INK, anchor="middle")
    canvas.text((S(50), S(80)), "AXONOMETRIC", S(12), GREY)
    canvas.text((S(1230), S(90)), "TOP", S(12), GREY)
    canvas.text((S(1230), S(470)), "ELEVATION (UNROLLED)", S(12), GREY)

    kind, key, event = state["kind"], state["key"], state["event"]
    current = None
    if event is not None and event["frame"] is not None and kind != "top_frame":
        current = (event["frame"], state["distance"])

    # Bricks to draw: (frame, distance, style)
    bricks = [(f, d, "placed") for (k_, (f, d)) in state["placed"]
              if (k_ != key or kind != "place")]
    if kind == "place":
        bricks.append((current[0], current[1], "current"))
    elif kind in ("reject_height", "reject_support"):
        bricks.append((current[0], current[1], "ghost"))
    elif kind in ("remove_isolated", "trim_base"):
        bricks = [b for b in bricks if not _same(b[0], current[0])]
        bricks.append((current[0], current[1], "removed"))

    def style(s):
        if s == "current":
            return dict(stroke=INK, width=S(2.4), fill=HILITE, dash=None)
        if s == "ghost":
            return dict(stroke=GREY, width=S(1.2), fill="none", dash=[S(5), S(4)])
        if s == "removed":
            return dict(stroke=INK, width=S(1.4), fill="none", dash=[S(5), S(4)])
        return dict(stroke=INK, width=S(1.0), fill="#ffffff", dash=None)

    # ---- axonometric: painter's algorithm, far bricks first ----
    order = [bricks[i] for i in paint_order([(b[0], None) for b in bricks], cam)]
    for frame, d, s in order:
        st = style(s)
        if s in ("ghost", "removed"):
            continue
        for poly in axon_polygons(frame, cam):
            canvas.polygon([f_axon(p) for p in poly], **st)
    for frame, d, s in order:
        if s in ("ghost", "removed"):
            st = style(s)
            for poly in axon_polygons(frame, cam):
                canvas.polygon([f_axon(p) for p in poly], **st)
            _cross(canvas, f_axon(cam.project(_xyz(frame.point))), S(7), st["stroke"], S(1.4))

    # ---- top view: lower bricks first ----
    for frame, d, s in sorted(bricks, key=lambda b: b[0].point.z):
        st = style(s)
        canvas.polygon([f_top(p) for p in top_polygon(frame)], **st)

    # ---- elevation (unrolled) ----
    for frame, d, s in bricks:
        st = style(s)
        canvas.polygon([f_elev(p) for p in elevation_polygon(frame, d)], **st)

    # ---- exposed top frames as dots ----
    for tf in state["tops"]:
        p = _xyz(tf.point)
        canvas.dot(f_axon(cam.project(p)), S(3.5), INK)
        canvas.dot(f_top((p[0], p[1])), S(3.0), INK)
    if kind == "top_frame":
        p = _xyz(event["frame"].point)
        a = f_axon(cam.project(p))
        canvas.dot(a, S(6), INK)
        _leader(canvas, a, "top frame  layer %d, i = %d" % (event["layer"], event["i"]), k)

    # ---- leader label on the current brick ----
    if current is not None:
        a = f_axon(cam.project(_xyz(current[0].point)))
        _leader(canvas, a, "layer %d, i = %d" % (event["layer"], event["i"]), k)

    # ---- counters (bottom left of the axon panel) ----
    c = state["counts"]
    lines = []
    if event is not None and event["layer"] is not None:
        lines.append("layer: %d    i: %d" % (event["layer"], event["i"]))
    lines.append("placed: %d    rejected: %d    removed: %d"
                 % (c["placed"], c["rejected"], c["removed"]))
    lines.append("bricks in wall: %d    top frames: %d" % (len(state["placed"]), c["tops"]))
    for n, s in enumerate(lines):
        canvas.text((S(60), S(720) + n * S(24)), s, S(16), INK)

    # ---- caption ----
    head, formula, note = STAGES[kind]
    if kind == "final":
        per_layer = {}
        for (layer, _), _v in state["placed"]:
            per_layer[layer] = per_layer.get(layer, 0) + 1
        formula = "   ".join("L%d: %d" % (l, per_layer[l]) for l in sorted(per_layer))
        note = "%d bricks, %d top frames" % (len(state["placed"]), c["tops"])

    canvas.line((S(50), S(812)), (S(1870), S(812)), LIGHT, S(1))
    canvas.text((S(60), S(868)), head, S(22), INK, bold=True)
    canvas.line((S(60), S(882)), (S(380), S(882)), INK, S(1.5))
    canvas.text((S(60), S(920)), formula, S(16), INK)
    canvas.text((S(1230), S(868)), note, S(16), INK)

    return canvas


def _same(f1, f2):
    a, b = f1.point, f2.point
    return abs(a.x - b.x) + abs(a.y - b.y) + abs(a.z - b.z) < 1e-6


def _cross(canvas, p, r, stroke, width):
    canvas.line((p[0] - r, p[1] - r), (p[0] + r, p[1] + r), stroke, width)
    canvas.line((p[0] - r, p[1] + r), (p[0] + r, p[1] - r), stroke, width)


def _leader(canvas, p, label, k):
    q = (p[0] - 70 * k, p[1] + 55 * k)
    canvas.line(p, q, INK, 1.0 * k)
    canvas.line(q, (q[0] - 12 * k, q[1]), INK, 1.0 * k)
    canvas.text((q[0] - 16 * k, q[1] + 5 * k), label, 14 * k, INK, anchor="end")


# ==========================================
# 6. EXPORT FRAME SEQUENCE
# ==========================================

def export_frames(states, folder, fmt="png", width=1920, height=1080,
                  frames_per_step=1, hold_stage=12, hold_end=36,
                  camera=None, title="From a Single Brick to Multiple Layers"):
    """
    Writes frame_00000.png ... into folder.
    hold_stage: extra frames when the stage title changes.
    hold_end:   extra frames on the last state.
    Returns the list of written paths.
    """

    if not os.path.isdir(folder):
        os.makedirs(folder)

    Canvas = PngCanvas if fmt == "png" else SvgCanvas

    paths = []
    previous_stage = None

    for n, state in enumerate(states):

        repeat = frames_per_step
        stage = STAGES[state["kind"]][0]
        if stage != previous_stage:
            repeat += hold_stage
        if n == len(states) - 1:
            repeat += hold_end
        previous_stage = stage

        first = None
        for _ in range(repeat):
            path = os.path.join(folder, "frame_%05d.%s" % (len(paths), fmt))
            if first is None:
                canvas = Canvas(width, height)
                render(state, canvas, title, camera, width, height)
                canvas.save(path)
                first = path
            else:
                _copy(first, path)
            paths.append(path)

    return paths


def _copy(src, dst):
    with open(src, "rb") as a, open(dst, "wb") as b:
        b.write(a.read())
