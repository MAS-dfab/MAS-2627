"""
Frames and speeds for non-planar layers.

Frames: Z (the nozzle) points down the wall onto the layer below, so it follows the surface.
The tilt is capped at max_tilt from straight down, so the nozzle never points up under a curled lip.
X always points as close as possible to one fixed direction in plan (x_dir), so the wrist does not spin.

Speeds, per point, based on the shape:
    thicker layer here -> slower, thinner -> faster (same material per mm: speed x height stays constant)
    wall leaning over (overhang) -> slower, down to 60% at 75 degrees and more
    short layers get slowed so every layer takes at least min_layer_time to print (time to set)
    all speeds stay between 40% and 150% of the base speed

Inputs:
    polylines       the layer polylines, in print order (one per layer, same points as printpath gets)
    form            the surface the layers lie on
    layer_height    the nominal layer height (mm)
    speed           base speed (mm/s) for a normal layer on a straight wall
    max_tilt        largest nozzle tilt from straight down (degrees, 45 is good)
    smooth          smoothing passes on the wall direction, keeps the wrist calm (10 is good)
    min_layer_time  seconds per layer at least, 0 = use the median layer of this shape
    max_speed       hard limit (mm/s); if any speed is above it, all speeds are scaled down together
    max_turn        the nozzle turns at most this many degrees per mm travelled (0.5 is good; lower = calmer wrist but further from the wall direction)
                    a UR movel slows the tip down when the tool turns faster than it moves
    tilt_ramp       height (mm) over which the allowed tilt grows from 0 (straight down at the table) to max_tilt
    x_dir           fixed X direction in plan, degrees from world +X (0 = +X, 180 = -X)
Outputs:
    planes          one frame per point, same order as the points
    speeds          one speed per point (mm/s)
    info            summary

Note: no lines starting with "- " in this docstring, Rhino 8's script component then loses RunScript.
"""
import math
import Rhino.Geometry as rg
import Grasshopper

PATH_SMOOTH = 50  # smoothing passes on the nozzle direction along the path, so the tilt never changes suddenly
DOWN = rg.Vector3d(0, 0, -1)


def as_points(pl):
    if isinstance(pl, rg.Polyline):
        return list(pl)
    ok, poly = pl.TryGetPolyline()
    return list(poly)


def wall_directions(layers, curves, face):
    """Per point: the direction in the surface from this layer towards the next one."""
    dirs = []
    for k, pts in enumerate(layers):
        row = []
        for i, p in enumerate(pts):
            t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            t.Unitize()
            ok, u, v = face.ClosestPoint(p)
            up = rg.Vector3d.CrossProduct(face.NormalAt(u, v), t)
            # which side is "up the wall": towards the next layer (or away from the previous for the last)
            if k < len(layers) - 1:
                ok, s = curves[k + 1].ClosestPoint(p)
                towards = curves[k + 1].PointAt(s) - p
            else:
                ok, s = curves[k - 1].ClosestPoint(p)
                towards = p - curves[k - 1].PointAt(s)
            if up * towards < 0:
                up.Reverse()
            up.Unitize()
            row.append(up)
        # keep the direction continuous along the layer (no sudden flips), starting from the middle
        mid = len(row) // 2
        for i in range(mid + 1, len(row)):
            if row[i] * row[i - 1] < 0:
                row[i].Reverse()
        for i in range(mid - 1, -1, -1):
            if row[i] * row[i + 1] < 0:
                row[i].Reverse()
        dirs.append(row)
    return dirs


def neighbour_index(layers, k, kk):
    """For each point of layer k, the index of the matching point on layer kk.
    Layers zigzag, so the same index can be at the opposite end: match by position along the layer."""
    a, b = layers[k], layers[kk]
    flipped = a[0].DistanceTo(b[-1]) < a[0].DistanceTo(b[0])
    n, m = len(a) - 1, len(b) - 1
    idx = [int(round(i * m / float(max(n, 1)))) for i in range(n + 1)]
    return [m - j for j in idx] if flipped else idx


def smooth_directions(dirs, layers, passes):
    """Average each direction with its neighbours along the layer and on the layers above and below."""
    below = [neighbour_index(layers, k, k - 1) if k > 0 else None for k in range(len(layers))]
    above = [neighbour_index(layers, k, k + 1) if k < len(layers) - 1 else None for k in range(len(layers))]
    for _ in range(passes):
        new = []
        for k in range(len(dirs)):
            row = []
            for i in range(len(dirs[k])):
                s = rg.Vector3d(dirs[k][i]) * 2
                for ii in (i - 1, i + 1):
                    if 0 <= ii < len(dirs[k]):
                        s += dirs[k][ii]
                if below[k]:
                    s += dirs[k - 1][below[k][i]]
                if above[k]:
                    s += dirs[k + 1][above[k][i]]
                s.Unitize()
                row.append(s)
            new.append(row)
        dirs = new
    return dirs


def limit_turning(zs, pts, max_turn):
    """Along the whole path, the nozzle may turn at most max_turn degrees per mm travelled.
    Forward and backward passes, so a sharp change is spread out on both sides."""
    for order in (range(1, len(zs)), range(len(zs) - 2, -1, -1)):
        for i in order:
            j = i - 1 if order.step > 0 else i + 1
            allowed = math.radians(max_turn) * max(pts[i].DistanceTo(pts[j]), 1e-6)
            ang = rg.Vector3d.VectorAngle(zs[j], zs[i])
            if ang > allowed:
                axis = rg.Vector3d.CrossProduct(zs[j], zs[i])
                if axis.Length < 1e-9:
                    continue
                z = rg.Vector3d(zs[j])
                z.Rotate(allowed, axis)
                zs[i] = z
    return zs


def capped(z, max_tilt):
    """Tilt z back to at most max_tilt degrees from straight down."""
    limit = math.radians(max_tilt)
    if rg.Vector3d.VectorAngle(z, DOWN) <= limit:
        return z, False
    axis = rg.Vector3d.CrossProduct(DOWN, z)
    if axis.Length < 1e-9:
        axis = rg.Vector3d(1, 0, 0)
    axis.Unitize()
    nz = rg.Vector3d(DOWN)
    nz.Rotate(limit, axis)
    return nz, True


class Script_Instance(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, polylines, form, layer_height, speed, max_tilt, smooth, min_layer_time, max_speed, max_turn, tilt_ramp, x_dir):
        if not polylines or form is None:
            return None, None, "connect polylines and form"
        max_turn = float(max_turn) if max_turn else 0.5
        lh = float(layer_height) if layer_height else 1.5
        base = float(speed) if speed else 20.0
        max_tilt = float(max_tilt) if max_tilt is not None else 45.0
        smooth = int(smooth) if smooth is not None else 10
        face = form.Faces[0] if isinstance(form, rg.Brep) else form

        layers = [as_points(pl) for pl in polylines]
        curves = [rg.PolylineCurve(p) for p in layers]
        raw = wall_directions(layers, curves, face)
        calm = smooth_directions(raw, layers, smooth)

        zs, all_pts, n_capped = [], [], 0
        for pts, row in zip(layers, calm):
            for p, up in zip(pts, row):
                z, was_capped = capped(-up, max_tilt)  # nozzle points down the wall
                n_capped += was_capped
                zs.append(z)
                all_pts.append(p)
        # near the table the nozzle points straight down, so the heater block / holder can not hit the table:
        # 0 deg tilt at z = 0, growing evenly to max_tilt at z = tilt_ramp
        tilt_ramp = float(tilt_ramp) if tilt_ramp else 30.0

        def height_cap(zs):
            return [capped(z, max_tilt * min(1.0, max(0.0, p.Z) / tilt_ramp))[0] for z, p in zip(zs, all_pts)]

        # smooth the tilt along the whole path (also across layer changes), so it changes a little every point
        zs = height_cap(zs)
        for _ in range(PATH_SMOOTH):
            zs = [zs[0]] + [zs[i - 1] + zs[i] * 2 + zs[i + 1] for i in range(1, len(zs) - 1)] + [zs[-1]]
            for z in zs:
                z.Unitize()
            zs = height_cap(zs)
        # then a hard limit on how fast it turns, and the height rule last so nothing can undo it
        zs = height_cap(limit_turning(zs, all_pts, max_turn))
        low = [math.degrees(rg.Vector3d.VectorAngle(z, DOWN)) for z, p in zip(zs, all_pts) if p.Z < 5.0]

        a = math.radians(float(x_dir) if x_dir is not None else 0.0)
        x_ref = rg.Vector3d(math.cos(a), math.sin(a), 0)
        planes = []
        for p, z in zip(all_pts, zs):
            x = x_ref - z * (x_ref * z)  # the fixed direction, made perpendicular to z
            x.Unitize()
            planes.append(rg.Plane(p, x, rg.Vector3d.CrossProduct(z, x)))
        turns = [math.degrees(rg.Vector3d.VectorAngle(zs[i], zs[i + 1])) /
                 max(all_pts[i].DistanceTo(all_pts[i + 1]), 1e-6) for i in range(len(zs) - 1)]

        # speed per point from local layer height and overhang
        layer_speeds = []
        for k, (pts, row) in enumerate(zip(layers, raw)):
            sp = []
            for p, up in zip(pts, row):
                h = lh
                if k > 0:
                    ok, s = curves[k - 1].ClosestPoint(p)
                    h = p.DistanceTo(curves[k - 1].PointAt(s))
                h = min(max(h, 0.5 * lh), 2.0 * lh)
                overhang = math.degrees(rg.Vector3d.VectorAngle(up, rg.Vector3d.ZAxis))  # 0 = wall goes straight up
                f_overhang = 1.0 if overhang <= 30 else max(0.6, 1.0 - 0.4 * (overhang - 30) / 45.0)
                sp.append(base * (lh / h) * f_overhang)
            layer_speeds.append(sp)

        # every layer at least min_layer_time seconds
        def layer_time(pts, sp):
            return sum(pts[i].DistanceTo(pts[i + 1]) / sp[i + 1] for i in range(len(pts) - 1))
        times = [layer_time(p, s) for p, s in zip(layers, layer_speeds)]
        t_min = float(min_layer_time) if min_layer_time else sorted(times)[len(times) // 2]
        speeds, slowed = [], 0
        for sp, t in zip(layer_speeds, times):
            factor = min(1.0, t / t_min)
            slowed += factor < 1.0
            speeds += [min(max(v * factor, 0.4 * base), 1.5 * base) for v in sp]

        # hard speed limit: scale everything down together so the differences stay the same
        if max_speed and max(speeds) > float(max_speed):
            scale = float(max_speed) / max(speeds)
            speeds = [v * scale for v in speeds]

        total = sum(layer_time(p, speeds[i0:i0 + len(p)]) for p, i0 in
                    zip(layers, [sum(len(q) for q in layers[:k]) for k in range(len(layers))]))
        info = "\n".join([
            "{} frames, {} capped at {:.0f} deg tilt".format(len(planes), n_capped, max_tilt),
            "turning at most {:.1f} deg per mm (limit {:.1f})".format(max(turns), max_turn),
            "below z = 5 mm the tilt is at most {:.1f} deg (straight down at z = 0, max_tilt from z = {:.0f})".format(
                max(low) if low else 0.0, tilt_ramp),
            "speed {:.1f} to {:.1f} mm/s (base {:.0f})".format(min(speeds), max(speeds), base),
            "min layer time {:.1f} s, {} layers slowed for it".format(t_min, slowed),
            "print time about {:.1f} min".format(total / 60.0),
        ])
        return planes, speeds, info
