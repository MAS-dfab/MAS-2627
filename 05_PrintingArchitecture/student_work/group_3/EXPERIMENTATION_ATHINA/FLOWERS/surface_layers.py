"""
Surface layers: non-planar print layers that follow the form.

Every layer is the set of points at the same distance from the base,
measured ALONG the surface, so the layers are evenly spaced on the surface
(over the hump and around curled lips) and end at the rim on both sides
instead of running down to the ground like this surface's isocurves do.

Inputs:
    form          Surface or single-face Brep; the base is its edge at v = min (on the ground)
    layer_height  distance between layers along the surface (mm)
    resolution    grid cells per side used to measure distances (150 is good, higher = smoother but slower)
    bridge        narrow folds up to this width (mm) get a straight bridge instead of a hook (3 is good, 0 = off)
    smooth        smoothing passes after bridging, rounds off the corners left at the bridges (20 is good)
Outputs:
    layers        print layers, bottom to top, all running the same direction
    info          layer count and how many hooks were bridged

Note: no lines starting with "- " in this docstring, Rhino 8's script component then loses RunScript.
"""
import heapq
import Rhino.Geometry as rg
import Grasshopper

# neighbours for the distance walk: 8 around + 8 knight moves (more directions = more accurate distances)
MIN_LENGTH = 15.0  # mm, shorter layers are skipped
EVEN_LOW = 0.85    # x layer height: closer to the layer below than this, the layer is pushed up
EVEN_HIGH = 1.3    # x layer height: further from the layer below than this, the layer is pulled down
FINAL_SMOOTH = 2   # smoothing passes after evening out (more = smoother but less even)

STEPS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1),
         (2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]


def to_face(geo):
    if isinstance(geo, rg.Brep):
        return geo.Faces[0]
    if isinstance(geo, rg.Surface):
        return geo
    return None


def distance_from_base(face, nu, nv):
    """Shortest distance over the surface from the base edge (v = min) to every grid point."""
    du, dv = face.Domain(0), face.Domain(1)
    us = [du.ParameterAt(i / float(nu)) for i in range(nu + 1)]
    vs = [dv.ParameterAt(j / float(nv)) for j in range(nv + 1)]
    pts = [[face.PointAt(u, v) for v in vs] for u in us]
    dist = [[float("inf")] * (nv + 1) for _ in range(nu + 1)]
    queue = []
    for i in range(nu + 1):
        for j in range(nv + 1):
            # the base row, plus side edges that collapse onto a base point
            on_collapsed_side = i in (0, nu) and pts[i][j].DistanceTo(pts[i][0]) < 1e-6
            if j == 0 or on_collapsed_side:
                dist[i][j] = 0.0
                queue.append((0.0, i, j))
    heapq.heapify(queue)
    while queue:
        d, i, j = heapq.heappop(queue)
        if d > dist[i][j]:
            continue
        for a, b in STEPS:
            x, y = i + a, j + b
            if 0 <= x <= nu and 0 <= y <= nv:
                if abs(a) + abs(b) == 3:  # knight move: go via the surface midpoint
                    mid = face.PointAt((us[i] + us[x]) / 2.0, (vs[j] + vs[y]) / 2.0)
                    nd = d + pts[i][j].DistanceTo(mid) + mid.DistanceTo(pts[x][y])
                else:
                    nd = d + pts[i][j].DistanceTo(pts[x][y])
                if nd < dist[x][y]:
                    dist[x][y] = nd
                    heapq.heappush(queue, (nd, x, y))
    return us, vs, dist


def level_lines(us, vs, dist, level):
    """Marching squares: the uv polylines where dist == level."""
    nu, nv = len(us) - 1, len(vs) - 1

    def cross(i0, j0, i1, j1):
        # point on the grid edge between two nodes where the distance equals `level`
        d0, d1 = dist[i0][j0], dist[i1][j1]
        t = (level - d0) / (d1 - d0)
        key = (min((i0, j0), (i1, j1)), max((i0, j0), (i1, j1)))
        uv = (us[i0] + t * (us[i1] - us[i0]), vs[j0] + t * (vs[j1] - vs[j0]))
        return key, uv

    links, coords = {}, {}
    for i in range(nu):
        for j in range(nv):
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            hits = []
            for k in range(4):
                a, b = corners[k], corners[(k + 1) % 4]
                if (dist[a[0]][a[1]] < level) != (dist[b[0]][b[1]] < level):
                    key, uv = cross(a[0], a[1], b[0], b[1])
                    coords[key] = uv
                    hits.append(key)
            for k in range(0, len(hits) - 1, 2):  # 2 hits = 1 segment, 4 hits (saddle) = 2 segments
                links.setdefault(hits[k], []).append(hits[k + 1])
                links.setdefault(hits[k + 1], []).append(hits[k])

    # chain the segments into polylines, starting from open ends first
    seen, chains = set(), []
    starts = [k for k, v in links.items() if len(v) == 1] + list(links.keys())
    for start in starts:
        if start in seen:
            continue
        chain, cur, prev = [start], start, None
        seen.add(start)
        while True:
            nxt = [n for n in links[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) > 2:
            chains.append([coords[k] for k in chain])
    return chains


def bridge_folds(pts, bridge, ratio=2.0, window=25.0):
    """Skip hooks into narrow folds: if the path comes back to within `bridge` mm of where it was
    after a much longer detour (> ratio x the gap, at most `window` mm), jump straight across."""
    arc = [0.0]
    for k in range(1, len(pts)):
        arc.append(arc[-1] + pts[k].DistanceTo(pts[k - 1]))
    out, i, cuts = [pts[0]], 0, 0
    while i < len(pts) - 1:
        best = i + 1
        for j in range(i + 2, len(pts)):
            detour = arc[j] - arc[i]
            if detour > window:
                break
            gap = pts[i].DistanceTo(pts[j])
            if gap < bridge and detour > ratio * max(gap, 1e-6):
                best = j  # keep looking: jump as far as the hook goes
        if best > i + 1:
            cuts += 1
        out.append(pts[best])
        i = best
    return out, cuts


def smooth_path(pts, passes, step=0.5):
    """Even spacing, then average each point with its neighbours (ends stay on the rim)."""
    crv = rg.PolylineCurve(pts)
    n = max(2, int(crv.GetLength() / step))
    p = [crv.PointAtNormalizedLength(k / float(n)) for k in range(n + 1)]
    for _ in range(passes):
        p = [p[0]] + [p[i] * 0.5 + (p[i - 1] + p[i + 1]) * 0.25 for i in range(1, len(p) - 1)] + [p[-1]]
    return p


def point_below(p, face, below_pts, tree, radius):
    """Nearest point of the layer below, measured along the surface: points across a narrow pleat
    (straight through the air, along the surface normal) are skipped."""
    ok, u, v = face.ClosestPoint(p)
    normal = face.NormalAt(u, v)
    best, best_d = None, float("inf")
    found = []
    tree.Search(rg.Sphere(p, radius), lambda s, e: found.append(e.Id))
    for i in found:
        q = below_pts[i]
        w = p - q
        d = w.Length
        if d < 1e-9 or d >= best_d:
            continue
        w.Unitize()
        if abs(w * normal) < 0.5:  # mostly along the surface
            best, best_d = q, d
    return best, best_d


def even_out(layers, face, layer_height, rounds=25, spread=3):
    """Bottom to top: push a layer up where it is too close to the layer below (< EVEN_LOW x layer height)
    and pull it down where it is too far (> EVEN_HIGH x layer height), measured along the surface.
    The shift is smoothed along the layer (`spread` passes), so the layer bends gently instead of getting a kink."""
    lo, hi = EVEN_LOW * layer_height, EVEN_HIGH * layer_height
    moved = 0
    for k in range(1, len(layers)):
        below_crv = layers[k - 1]
        below = [below_crv.PointAtNormalizedLength(j / 400.0) for j in range(401)]  # dense, 0.1 to 0.5 mm
        tree = rg.RTree()
        for j, q in enumerate(below):
            tree.Insert(q, j)
        pts = [layers[k].Point(i) for i in range(layers[k].PointCount)]
        for _ in range(rounds):
            shifts, any_off = [], False
            for p in pts:
                q, d = point_below(p, face, below, tree, 3 * layer_height)
                if q is None:
                    shifts.append(rg.Vector3d(0, 0, 0))
                    continue
                target = min(max(d, lo), hi)
                if abs(target - d) < 1e-3 or d < 1e-6:
                    shifts.append(rg.Vector3d(0, 0, 0))
                    continue
                away = p - q
                away.Unitize()
                shifts.append(away * (target - d))
                any_off = True
            if not any_off:
                break
            for _ in range(spread):
                shifts = [shifts[0]] + [shifts[i] * 0.5 + (shifts[i - 1] + shifts[i + 1]) * 0.25
                                        for i in range(1, len(shifts) - 1)] + [shifts[-1]]
            # shifts are small and along the surface, so the points stay on it; snapping them back onto
            # the surface is not done on purpose: in narrow pleats it jumps to the other side of the fold
            moved += sum(1 for s in shifts if s.Length > 0.05)
            pts = [p + s for p, s in zip(pts, shifts)]
        # light smoothing at the end (in place, no resampling), so neighbouring shifts can not leave a kink
        for _ in range(FINAL_SMOOTH):
            pts = [pts[0]] + [pts[i] * 0.5 + (pts[i - 1] + pts[i + 1]) * 0.25 for i in range(1, len(pts) - 1)] + [pts[-1]]
        layers[k] = rg.PolylineCurve(pts)
    return layers, moved


class Script_Instance(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, form, layer_height, resolution, bridge, smooth):
        layer_height = float(layer_height) if layer_height else 1.5
        n = int(resolution) if resolution else 150
        bridge = float(bridge) if bridge is not None else 3.0
        smooth = int(smooth) if smooth is not None else 20
        face = to_face(form)
        if face is None:
            return None, "connect a Surface or single-face Brep to 'form'"

        us, vs, dist = distance_from_base(face, n, n)
        top = max(max(row) for row in dist)

        layers, bridged = [], 0
        level = layer_height * 0.5
        while level < top:
            for chain in sorted(level_lines(us, vs, dist, level), key=len, reverse=True):
                pts = [face.PointAt(u, v) for u, v in chain]
                if bridge > 0:
                    pts, cuts = bridge_folds(pts, bridge)
                    bridged += cuts
                if smooth > 0:
                    pts = smooth_path(pts, smooth)
                crv = rg.PolylineCurve(pts)
                if crv.GetLength() < MIN_LENGTH:
                    continue  # tiny scraps at the very top: 60 points on a few mm = tiny moves, the wrist spins
                # same direction as the layer before, so Dispatch/Flip downstream can zigzag
                if layers and layers[-1].PointAtStart.DistanceTo(crv.PointAtEnd) < layers[-1].PointAtStart.DistanceTo(crv.PointAtStart):
                    crv.Reverse()
                layers.append(crv)
            level += layer_height

        layers, evened = even_out(layers, face, layer_height)

        info = "{} layers, {:.0f} mm from base to the farthest rim point\n{} hooks into narrow folds bridged\n{} point shifts to even out the layer height ({:.2f} to {:.2f} mm)".format(
            len(layers), top, bridged, evened, EVEN_LOW * layer_height, EVEN_HIGH * layer_height)
        return layers, info
