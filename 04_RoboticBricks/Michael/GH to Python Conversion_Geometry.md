# GH to Python Conversion – Geometry

**File:** `04_RoboticBricks/Michael/Robotic Tower.gh`
**Sessions:** 2026-10-21 (rebuild of the native definition) · 2026-10-21/22 (bond, frames, stacking, profile calibration)
**Goal:** Understand the existing native-Grasshopper tower definition (rings → divided by projected brick length), fix its problems, and rebuild it stage by stage as lean GH Python 3 components. Then extend it into a brick assembly: twist, brick bond, clash culling between towers, compas frames and bricks, and a profile calibrated so the bricks stack.

The original native components are still on the canvas (the definition group is deactivated) for comparison and revert. The Python rebuild is in the blue **"Python rebuild"** group.

---

## 1. The original definition: stages

| Stage | What it does | Main native components |
|---|---|---|
| 0. Setup | LAMCP bridge (127.0.0.1:8765) and COMPAS auto-reload of `brick_wall.py` | LAMCP, Enable auto-reload |
| 1. Site and towers | Site X/Y, edge offset and spacing → checkerboard grid of tower centres | Diagrid (Python), Rectangle, Pt, pDecon (graft) |
| 2. Brick configs → module rhythm | Two `Brick` orientations → 4 sub-level heights and a module step | 2× Brick Dimensions (Python), Cluster Heights, Series, Flip |
| 3. Profile | Graph Mapper samples → radius per level and rotation angle per level | Range (hidden `x-1`), Graph Mapper, Bnd, Dom ×2, `x*y`, Rad, ReMap ×2 |
| 4. Rings | Per-tower phase shift of the profile, Z levels, circles | Index, Lng, `x%z`, Shift List ×2, Series, Pt, Circle |
| 5. Division | Circumference ÷ half projected brick length → even count → division points | Len, `½·(x·cos(y)+gap)`, `((c/p)\2)*2`, Divide Curve |

### What each Cluster Heights output meant (original)
With brick heights a and b, `module_h = [0, ½|a−b|, ½(a+b), max(a,b)]` and `step = a+b`: the bottom and top faces of each brick, with both bricks centred on a shared mid-plane. **Superseded in session 2** (see 4.2): the levels are now stacked top faces.

### Count formula (original)
`((c/p)\2)*2` with `p = ½·(L·cosθ + gap)` works out to `2 · floor(c / (L·cosθ + gap))`: always even, two points per brick slot. **Superseded in session 2** by the footprint spacing rule (see 4.6).

---

## 2. Problems found in the original definition (all fixed by the user)

1. **The projected length used the ring radius instead of the brick length.** x in `½·(x·cos(y)+gap)` was wired from the radius ReMap. It's now wired from Brick Dimensions (Config 1) `length`.
2. **Division counts were paired with the wrong rings.** The circles used *shifted* radii (9 branches × 14), but the projected length used *unshifted* radii and angles (one flat list of 14). Fixed with a second Shift List on the angles.
3. **The shift expression didn't do what it seemed to.** `int((x%(z\2))*max(x))` was replaced with `x%z`.
4. **Two sliders were both called `min_radius`.** The Diagrid one was renamed `offset`.
5. **A stray `Format("{0}, {1}", x, y)` expression with no inputs** was deleted.

---

## 3. User preferences and working rules (apply to future components)

- **Plain-script GH Python 3:** no `Script_Instance` class and no helper defs. Inputs are globals and outputs are assigned variables. Use a simple list comprehension where one will do; a short loop where a value depends on the previous one. Don't over-engineer.
- **No hard-coded design values.** Every slider, value list, panel and Graph Mapper stays **outside** the component as an editable input.
- **Faint wires** on every new input. **Matched data-tree paths** via `ghpythonlib.treehelpers`.
- **Never delete the user's existing components.** Build alongside; disconnected leftovers stay on the canvas.
- **Stage the work: one component per stage, review with the user before the next.** Ask clarifying questions before implementing.
- **Formulas must not be specific to Config 1 and 2.** Logic has to work for any number of configs (use `pattern` / `orient`).
- **Flag clash and stacking risks** whenever geometry changes; verify on the real canvas, not only in emulation.
- The user renames components and outputs after they're built. Always re-read the canvas before referring to names.
- Converting to compas frames for **assembly rules / pick-and-place** is left to the user (Brick Frames outputs plain compas `Frame`s).

---

## 4. The Python rebuild (current state, 2026-10-22)

```
X/Y Size, offset, spacing ─► Diagrid and Site ─► points ──────────────────────────────┐
configs, pattern, Modules ─► Module Information ─► t ─► Graph (Bezier) ─► Radii and Rotations ─► radii, angles ─► Rings ◄─ step
        │                                                                                     rings, ring_angles │
        ├─ lengths, widths ── orient panel ── gap ─────────────────────────────► Curve Division ◄──────────────────┤
        │                                                                 points, tangents │                      │
        │                                                     shift slider ─► Rotate Points ◄── rings ────────────┤
        │                                                         rot_points, rot_tangents │                      │
        ├─ module_h ─────────────────────────────────── bond slider ─► Brick Bond                                 │
        │                                    bond_points, bond_tangents (per sub-level) │                         │
        ├─ lengths, widths ── gap ──────────────────────────────────► Clash Detection ◄── rings ──────────────────┤
        │                                                     kept_points, kept_tangents │                        │
        └─ configs, pattern, orient ────────────────────────────────► Brick Frames ◄── ring_angles ───────────────┘
                                                                     frames, bricks ─► COMPAS: Draw ×2
```

### Current external inputs

| Input | Value | Notes |
|---|---|---|
| x_bound / y_bound / offset | 420 / 594 / 100 | unchanged |
| spacing | **130** (was 77) | 4 towers (was 9) |
| Config 1 / Config 2 | `configuration(0)` flat 32×15.2×9.85 / `configuration(1)` on edge 32×9.85×15.2 | value lists |
| pattern panel | `1,2,2,1` | config per sub-level (slot) |
| orient panel (new) | `T,R,R,T` | T = length along the tangent, R = length to the ring centre |
| Modules | 8 | |
| Graph (rebuild) | **Bezier** (0, 0.387), (0.807, 0.708), (0.362, 0.891), (1, 0.458) | original Sine kept in the locked native mapper |
| min_radius / factor / Degrees | **51.28 / 1.43 / 15** (was 45.25 / 1.601 / 30) | |
| gap | **2** (was 1; integer slider) | |
| shift (new) | 1 (integer 0–4) | replaces `rotation` (old slider left unconnected) |
| bond (new) | 2 (integer 1–2) | 1 = no alternation |

### 4.1 Diagrid and Site (stage 1) — unchanged
Inputs: `x_bound`, `y_bound`, `offset`, `spacing` (item). Outputs: `site`, `points`.
```python
import Rhino.Geometry as rg

# Site boundary
site = rg.Rectangle3d(rg.Plane.WorldXY, x_bound, y_bound).ToNurbsCurve()

# Usable grid snapped to multiples of spacing, centred on the site
x_dim = (x_bound - 2 * offset) // spacing * spacing
y_dim = (y_bound - 2 * offset) // spacing * spacing
off_x = (x_bound - x_dim) / 2
off_y = (y_bound - y_dim) / 2

# Checkerboard cells -> one centre point per tower (row by row)
points = [
    rg.Point3d(off_x + spacing * col, off_y + spacing * row, 0.0)
    for row in range(int(y_dim // spacing) + 1)
    for col in range(int(x_dim // spacing) + 1)
    if col % 2 == row % 2
]
```

### 4.2 Module Information (stage 2) — `module_h` redefined in session 2
Inputs: `configs` (list), `pattern` (list, 1-based), `modules` (item). Outputs: `length` (now unused), `lengths`, `widths`, `module_h`, `step`, `levels`, `t`.
```python
# r: compas
# venv: mas-2627
from compas_rhino.devtools import DevTools
DevTools.ensure_path()

from brick_wall import Brick

# One brick per config; pattern holds 1-based positions in configs (e.g. 1,2,2,1)
bricks = []
for c in configs:
    b = Brick()
    b.configuration(c)
    bricks.append(b)
slots = [bricks[int(p) - 1] for p in pattern]

length = slots[0].length
lengths = [b.length for b in slots]
widths = [b.width for b in slots]

# Sub-levels as brick top faces: levels 1-2 start on the module base, each level sits on the one two below it
module_h = []
for s, b in enumerate(slots):
    module_h.append((module_h[s - 2] if s >= 2 else 0) + b.height)
used = [bricks[i] for i in sorted({int(p) - 1 for p in pattern})]
step = sum(b.height for b in used)

# All sub-levels, module by module
n = int(modules)
levels = [m * step + h for m in range(n) for h in module_h]

# Normalised level parameters (0..1) for the Graph Mapper
t = [i / (n - 1) for i in range(n)]
```
`module_h` = [9.85, 15.2, 25.05, 25.05], `step` = 25.05. Even points hold L1 T (0–9.85) + L3 R (9.85–25.05); odd points hold L2 R (0–15.2) + L4 T (15.2–25.05). Each point column is one T + one R per module, exactly one `step` tall, with no voids or overlaps.

### 4.3 Graph (rebuild Graph Mapper)
Fed by `Module Information.t`. Switched from Sine to **Bezier** in stage B3 (see section 6). The original Sine stays in the locked native mapper.

### 4.4 Radii and Rotations (stage 3) — unchanged
```python
import math

# Source domain = actual bounds of the graph values, normalised to 0..1
g_min, g_max = min(graph), max(graph)
norm = [(g - g_min) / (g_max - g_min) for g in graph]

# Remap the profile to a radius and a rotation angle per level
r_max = min_radius * factor
radii = [min_radius + n * (r_max - min_radius) for n in norm]
angles = [math.radians(-degrees + n * 2 * degrees) for n in norm]
```
The profile is normalised, so only its **shape** matters. Its amplitude is set by `factor` (radius) and `Degrees` (angle), both driven by the same normalised value.

### 4.5 Rings (stage 4) — unchanged
```python
import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

n = len(radii)

# Per tower: profile shifted by the tower index (wrapped, as Shift List with x%z)
rings = th.list_to_tree([
    [rg.Circle(rg.Point3d(p.X, p.Y, k * step), radii[(k + i) % n]) for k in range(n)]
    for i, p in enumerate(points)
])
ring_angles = th.list_to_tree([
    [angles[(k + i) % n] for k in range(n)]
    for i in range(len(points))
])
```

### 4.6 Curve Division (stage 5) — footprint spacing + count lock
Inputs: `rings`, `ring_angles` (tree), `lengths`, `widths`, `orient` (list), `gap` (item). Outputs: `points`, `tangents`, `params` (`{0;tower;module}`).
```python
import math
import ghpythonlib.treehelpers as th

ring_list = th.tree_to_list(rings)
angle_list = th.tree_to_list(ring_angles)

dirs = [o.strip() for o in orient]

# Spacing between neighbouring points: half the footprints along the ring of two consecutive levels, plus gap
# Footprint after the plan turn a: T = length*|cos a| + width*|sin a|, R = length*|sin a| + width*|cos a|
counts = []
for cs, aa in zip(ring_list, angle_list):
    tower = []
    for c, a in zip(cs, aa):
        cos_a, sin_a = abs(math.cos(a)), abs(math.sin(a))
        foot = [l * cos_a + w * sin_a if d == "T" else l * sin_a + w * cos_a for l, w, d in zip(lengths, widths, dirs)]
        spacing = max((foot[s] + foot[s + 1]) / 2 for s in range(len(foot) - 1)) + gap
        tower.append(int(c.GetLength() / spacing // 2 * 2))
    counts.append(tower)

# Same count on every ring of a tower (its smallest), so the points line up between modules
counts = [[min(ns)] * len(ns) for ns in counts]
t = [[list(c.DivideByCount(n, True)) for c, n in zip(cs, ns)] for cs, ns in zip(ring_list, counts)]

points = th.list_to_tree([[[c.PointAt(x) for x in ts] for c, ts in zip(cs, tt)] for cs, tt in zip(ring_list, t)])
tangents = th.list_to_tree([[[c.TangentAt(x) for x in ts] for c, ts in zip(cs, tt)] for cs, tt in zip(ring_list, t)])
params = th.list_to_tree(t)
```
- **Floor rounding** (session 1, item 1): kept as Python's `//`. The native group is not matched to it.
- The **sin θ terms are essential**: an R brick turned 30° covers 24.5 along the ring, not 9.85. A cos-only rule still clashed (250 pairs, up to 7.9 deep).
- **Count lock (B1):** every ring of a tower gets the smallest count. Larger rings therefore spread their bricks wider (see section 8).

### 4.7 Rotate Points — twist by whole point spacings
Inputs: `rings`, `points`, `tangents` (tree), `shift` (item). Outputs: `rot_points`, `rot_tangents`.
```python
import math
import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

ring_list = th.tree_to_list(rings)
pt_list = th.tree_to_list(points)
tan_list = th.tree_to_list(tangents)

# Twist: each circle turns `shift` point spacings (360 / points on its ring) further than the one below,
# so every module lands on the points of the module below
xforms = [
    [rg.Transform.Rotation(2 * math.pi / len(ps) * shift * k, c.Arc.Plane.ZAxis, c.Arc.Center) for k, (c, ps) in enumerate(zip(cs, pss))]
    for cs, pss in zip(ring_list, pt_list)
]

rot_points = th.list_to_tree([[[x * p for p in ps] for x, ps in zip(xs, pss)] for xs, pss in zip(xforms, pt_list)])
rot_tangents = th.list_to_tree([[[x * v for v in vs] for x, vs in zip(xs, vss)] for xs, vss in zip(xforms, tan_list)])
```
History:
- Session 1: `rotation / circles · k`.
- Session 2, stage 1: `rotation / (circles − 1) · k`, so the top circle reaches the slider value.
- Stage B2: `shift` point spacings per module. With `shift` = 1, L1 (T) lands on L4 (T) below and L2 (R) on L3 (R): same-orientation contact between modules.

### 4.8 Brick Bond (new) — alternation per level + copy to sub-levels
Inputs: `points`, `tangents` (tree), `bond` (item), `module_h` (list). Outputs: `bond_points`, `bond_tangents` (`{0;tower;sub-level}`).
```python
import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

pt_list = th.tree_to_list(points)
tan_list = th.tree_to_list(tangents)
n = int(bond)
m = len(module_h)

# Copy each module ring to its sub-levels (brick top faces) and alternate per level, regardless of module:
# level g = module * m + sub-level keeps the points whose index matches g (every n-th point)
bond_points = th.list_to_tree([
    [[p + rg.Vector3d(0, 0, h) for j, p in enumerate(ps) if j % n == (k * m + s) % n] for k, ps in enumerate(pss) for s, h in enumerate(module_h)]
    for pss in pt_list
])
bond_tangents = th.list_to_tree([
    [[v for j, v in enumerate(vs) if j % n == (k * m + s) % n] for k, vs in enumerate(vss) for s in range(m)]
    for vss in tan_list
])
```
It must run **before** Clash Detection: culling single points would shift the even/odd indices.

### 4.9 Clash Detection (renamed from Cull Points) — per sub-level input, plan check per module
Inputs: `rings`, `points`, `tangents` (tree), `lengths`, `widths` (list), `gap` (item). Outputs: `kept_points`, `kept_tangents` (`{0;tower;sub-level}`).
```python
import math
import ghpythonlib.treehelpers as th

ring_list = th.tree_to_list(rings)
pt_list = th.tree_to_list(points)
tan_list = th.tree_to_list(tangents)
towers, levels = len(ring_list), len(ring_list[0])
m = len(pt_list[0]) // levels

# Clearance between towers: largest brick plan diagonal in the pattern + gap
threshold = max(math.hypot(l, w) for l, w in zip(lengths, widths)) + gap

# Per module, larger rings win: go from largest to smallest radius (ties keep tower order) and keep a point
# only if it clears, in plan, every point already kept on other rings in any sub-level of that module
keep = [[None] * len(pt_list[0]) for _ in range(towers)]
for k in range(levels):
    kept = []
    for i in sorted(range(towers), key=lambda i: -ring_list[i][k].Radius):
        for s in range(k * m, (k + 1) * m):
            keep[i][s] = [all(math.hypot(p.X - q.X, p.Y - q.Y) >= threshold for q in kept) for p in pt_list[i][s]]
        kept += [p for s in range(k * m, (k + 1) * m) for p, ok in zip(pt_list[i][s], keep[i][s]) if ok]

kept_points = th.list_to_tree([[[p for p, ok in zip(ps, ks) if ok] for ps, ks in zip(pss, kss)] for pss, kss in zip(pt_list, keep)])
kept_tangents = th.list_to_tree([[[v for v, ok in zip(vs, ks) if ok] for vs, ks in zip(vss, kss)] for vss, kss in zip(tan_list, keep)])
```
Modules don't overlap in height (each starts on the 25.05 plane of the one below), so only the sub-levels of the same module are compared.

### 4.10 Brick Frames (new) — compas frames and bricks + COMPAS: Draw ×2
Inputs: `points`, `tangents`, `ring_angles` (tree), `configs`, `pattern`, `orient` (list). Outputs: `frames` (compas `Frame`), `bricks` (compas `Box` via `Brick.draw()`), `{0;tower;sub-level}`.
```python
# r: compas
# venv: mas-2627
from compas_rhino.devtools import DevTools
DevTools.ensure_path()

import math
import ghpythonlib.treehelpers as th
from compas.geometry import Frame, Point, Vector
from brick_wall import Brick

pt_list = th.tree_to_list(points)
tan_list = th.tree_to_list(tangents)
angle_list = th.tree_to_list(ring_angles)

# Pattern slot = sub-level within a module: its config and orientation (T = tangential, R = radial)
slots = [configs[int(p) - 1] for p in pattern]
dirs = [o.strip() for o in orient]
m = len(slots)

z = Vector(0, 0, 1)
frame_list, brick_list = [], []
for i, levels in enumerate(pt_list):
    tower_frames, tower_bricks = [], []
    for s, pts in enumerate(levels):
        a = angle_list[i][s // m]
        level_frames, level_bricks = [], []
        for p, t in zip(pts, tan_list[i][s]):
            b = Brick()
            b.configuration(slots[s % m])
            # Length along the tangent (T) or inward to the ring centre (R), then turned in plan by the ring angle
            x = Vector(t.X, t.Y, 0).unitized()
            if dirs[s % m] == "R":
                x = z.cross(x)
            x = x * math.cos(a) + z.cross(x) * math.sin(a)
            # Points mark the top face: frame sits at the brick centre
            b.frame = Frame(Point(p.X, p.Y, p.Z - b.height / 2), x, z.cross(x))
            level_frames.append(b.frame)
            level_bricks.append(b.draw())
        tower_frames.append(level_frames)
        tower_bricks.append(level_bricks)
    frame_list.append(tower_frames)
    brick_list.append(tower_bricks)

frames = th.list_to_tree(frame_list)
bricks = th.list_to_tree(brick_list)
```
- **Frame convention** (matches `Brick.draw()` / `get_pick_frame()`):
  - origin at the brick centre (top-face point − height/2);
  - x = length, y = width, z = up;
  - R bricks point inward. They're symmetric under a 180° turn.
- **Display:** two COMPAS: Draw components (`Draw frames`, `Draw bricks`), about 0.9 s and 0.7 s per solve.

---

## 5. Session 2 log (2026-10-21 → 22)

| Stage | Change | Outcome |
|---|---|---|
| 1 | Floor rounding confirmed; Rotate Points `/(n−1)` | Top circle reaches the slider value. Found and fixed Rotate Points inputs set to "ghdoc Object" (Guids instead of curves). |
| 2 | **Brick Bond** added (bond = 2, per module row) | 1,584 → 792 points; clash test on bond points only (closed old item 11). |
| 3 | **Brick Frames** + `orient` panel + COMPAS Draw | Frames correct, but a 3D box test found heavy clashes: all 4 levels shared the same points, `module_h` came from the mid-plane construction, and the L·cosθ spacing ignored W·sinθ. |
| — | Design clarified by the user | Levels are **top faces**. L1 T and L2 R share the module's bottom plane; L3 R and L4 T share its top plane. Alternation is **per level, regardless of module**. Spacing must exceed the projected footprints plus the gap. |
| 4a | Module Information: stacked `module_h` | [9.85, 15.2, 25.05, 25.05]. Bricks start at z = 0, columns contiguous. |
| 4b | Curve Division: footprint spacing rule | 0 clashes within towers (simulated, then confirmed). Counts 18–30 → 8–14 per ring. |
| — | **Stacking check** requested | Within a module safe. Between modules, 248 of 712 bricks would tip: radius jumps over ~7.6, changing point counts, twist misalignment. |
| 4c | Brick Bond: per-level parity + copy to sub-levels | 810 → 1,620 points (each point used by 2 of 4 levels). |
| 4d | Clash Detection: per sub-level, plan check across the module | **0 clashes** within and between towers (1,084 bricks). The cull made stacking worse: 79 floating, 232 at risk. |
| — | 60 % contact criterion tested | **Impossible with T/R crossing**: contact is fixed at 47.5 % (R on T) and 30.8 % (T on R). User chose criterion (a): centre over support **and** ≥ 30 % contact. |
| — | Profile calibration (section 6) | Chose **B: two component changes + B-Bezier**. |
| B1 | Curve Division: count lock per tower | 1,084 → 766 bricks, 0 clashes. |
| B2 | Rotate Points: `shift` point spacings | Weak 184 → 79 (current profile), 0 clashes. |
| B3 | Bezier graph + slider values | **640 bricks, 0 clashes, 0 weak, 0 floating.** Canvas identical to the emulator. |
| — | **Design review by the user** (section 8) | Result is structurally "valid" but visually wrong. Alternatives listed in section 11. |

---

## 6. Profile calibration (stage B, 2026-10-22)

**Method.** The whole chain (Diagrid → Brick Frames) was re-implemented in the bridge session as an emulator. It reproduced the canvas exactly: 1,084/1,084 bricks before B1, and 640/640 after B3. Two checks were run on every candidate:
- a **3D box clash test** (separating axes in plan plus height-interval overlap);
- a **support test**: for every brick above ground, the contact polygons with bricks whose top equals its bottom, the contact share of its footprint, and whether its centre lies inside the convex hull of the contacts.

Graphs were built from their serialised parameters. About 4,300 candidates were tried over Sine, Bezier and Conic grips, `Modules`, `min_radius`, `factor`, `Degrees`, `rotation`/`shift`, `spacing` and `gap`. The emulator only lives in the bridge session and is not saved to the repo.

**Findings**
1. **Radius step between consecutive modules (including the wrap-around from the per-tower profile shift) must stay under about 7.6**, half a T brick's width. Above about 8, almost nothing passes. The graph type matters less than the step size.
2. **Point count changes between rings** break vertical alignment. Fixed by the count lock (B1).
3. **The twist must be a whole number of point spacings** (B2). Then modules stack T on T and R on R.
4. **Ring curvature:** on small rings (r ≈ 43) at 0° ring angle, R and T neighbours clash by up to 1.1. The spacing rule is measured along the ring. Open item.
5. **Brick count** falls mostly with fewer towers (`spacing`) and fewer modules.

**Candidates** (all with 0 clashes, 0 weak, 0 floating):

| | Graph | Bricks | Towers / modules | Radius range | Degrees | Contact between modules (min / mean) |
|---|---|---|---|---|---|---|
| A (components unchanged) | Sine | 312 | 2 / 5 | 58–64 | 2 | 32 % / 60 % |
| A | Bezier | 576 | 6 / 6 | 40–49 | 21 | 33 % / 42 % |
| A | Conic | 576 | 6 / 6 | 40–47 | 17 | 32 % / 44 % |
| B (count lock + shift) | Sine | 320 | 2 / 8 | 46–65 | 10 | 50 % / 73 % |
| **B – chosen** | **Bezier** | **640** | **4 / 8** | **51–73** | **15** | **54 % / 68 %** |
| B | Conic | 672 | 4 / 7 | 47–57 | 6 | 36 % / 85 % |

---

## 7. Current check (after B3, 2026-10-22)

- 4 towers × 8 modules, **10 points on every ring**.
  - Tower 0 radii: 51.3, 55.5, 60.4, 66.5, 73.3, 69.8, 63.0, 56.2.
  - Ring angles: −15 … +15°.
- **640 bricks**, identical to the emulator. No runtime messages on the canvas.
- **0 clashes** within and between towers.

| Level | Bricks | Weak | Floating | Contact min / mean |
|---|---|---|---|---|
| L1 (T on module below) | 140 | 0 | 0 | 54 % / 62 % |
| L2 (R on module below) | 140 | 0 | 0 | 68 % / 74 % |
| L3 (R on L1) | 160 | 0 | 0 | 47.5 % |
| L4 (T on L2) | 160 | 0 | 0 | 30.8 % |
| On the ground | 40 | – | – | – |

Approximate solve times: Brick Frames 254 ms, Brick Bond 93 ms, Clash Detection 91 ms, Curve Division 85 ms, Draw frames 0.9 s, Draw bricks 0.7 s.

---

## 8. Design review (user, 2026-10-22)

> **"No longer has the effect of intersecting volumes. Pieces are also too separate to read as solid mass and visually precarious despite claims of no weak or floating bricks."**

What causes each point, as measured on the current tower:

1. **No intersecting volumes.**
   - The original read came from T and R bricks sharing points, so the volumes interpenetrated. Physically those were clashes.
   - The spacing rule now separates the footprints of consecutive levels by at least the gap.
   - The only remaining crossing is vertical: R on T within a column. In plan nothing overlaps.
2. **Too separate to read as mass.**
   - The count lock fixes every ring to the smallest ring's count (10), so larger rings spread out. The clear gap between neighbouring T and R footprints along the ring grows from **5.9 on the smallest ring to 19.8 on the largest**, against the 2 required. Unlocked, the large rings would hold 16 points instead of 10.
   - Alternation per level leaves every other position empty on each level.
   - Fewer towers (4) and smaller ring angles thin the read further.
3. **Visually precarious.**
   - "0 weak / 0 floating" only means the rigid-block test passed: centre over support and ≥ 30 % contact. That threshold was relaxed from the user's 60 %, which the T/R crossing can never reach.
   - L4 T bricks rest on **30.8 %** of their underside, on a single crossing R brick. L3 R bricks rest on 47.5 %.
   - Each point column is an **independent slender pier** (one T + one R per module). No brick bridges between neighbouring columns, so there's no lateral interlock.
   - The check does not cover adhesive, lateral load, placement tolerance (measured brick sizes vary) or robot contact forces. Visual precariousness reflects a real lack of redundancy.

**Conclusion:** the current concept (T/R crossing at the same point, alternating columns) can be made clash-free and statically passable, but only by separating the bricks. That works against both the intersecting read and the solid mass. Section 11 lists alternatives.

---

## 9. Decisions (and why)

| Decision | Reason |
|---|---|
| One Python component per stage; stage 0 not converted | Matches the outlined stages, with nothing extra. |
| Wire new components to the **existing** sliders and value lists | Old and new chains ran on identical inputs for comparison. |
| Graph Mapper kept as an external input; `t` from Module Information | Profile stays hand-editable. |
| Rhino.Geometry up to Clash Detection, compas from Brick Frames | Display in GH; compas frames for robotics. |
| `pattern` input (1-based) instead of config-specific formulas | Any number of configs or pattern length. |
| Floor rounding for counts; native group not matched | User: Python version is the intended one. |
| Rotate Points before Clash Detection | The cull must test the twisted positions. |
| **Levels = top faces; L1/L2 share the bottom plane, L3/L4 the top plane** | User definition. One T + one R per point per module, exactly `step` tall. |
| **`orient` panel per slot (`T,R,R,T`)** | User preference: easy to read. Avoids hard-coding "Config 2 = radial". |
| R bricks point inward | Bricks are symmetric under a 180° turn. |
| **Alternation per level, regardless of module** | User rule. Even points carry L1 + L3, odd points carry L2 + L4. |
| Bond + sub-level copy in Brick Bond, before Clash Detection | Culling first would shift the even/odd indices. |
| **Spacing = largest ½(e_a + e_b) over consecutive slots + gap, with full rotated footprints** | User: spacing must exceed projected distance + gap. A cos-only rule still clashed. |
| Clash Detection compares across all sub-levels of a module, in plan | Bricks within a module overlap in height. Modules don't. |
| Structural criterion (a): centre over support **and** ≥ 30 % contact | 60 % is impossible with the T/R crossing. User chose to keep the bond. |
| Floating bricks from the cull: parked | Handling them means removing more bricks, never re-adding culled ones (that would bring the clashes back). |
| **Count lock per tower (B1) and `shift` point spacings (B2)** | 5× pass rate in calibration; same-orientation contact between modules. |
| **B-Bezier profile** | Closest to the original radius range (51–73 vs 45–72) at 640 bricks. |
| `gap` = 2 instead of 1.9 | Integer slider. Identical result in emulation, so the slider type was left as is. |

---

## 10. Pitfalls and lessons learned

**Grasshopper**
- **Hidden input expressions** (Range `N` had `x-1` on the input). Inspect input expressions.
- **A clean solve isn't a correct solve.** Check data counts and paths, not just warnings.
- **`\` in GH Expressions rounds the left operand first** (VB-style). Python's `//` floors. Re-verify after changing inputs.
- **Re-check equivalence whenever sliders change.** Read slider values before interpreting counts.
- **Flatten/graft flags** change paths silently. **Panels as data relays** convert numbers to text.
- **A duplicated Graph Mapper doesn't stay linked** to the original.
- **`GH_GraphMapper.Graph` has no setter.** In Python, `gm.Graph = g` silently sets an attribute on the wrapper only, and the mapper keeps its old graph and output. Set it through the container: `gm.GetType().GetField('m_container', …).GetValue(gm).Graph = g`, then expire. The container also holds the X/Y domains (`X0`, `X1`, `Y0`, `Y1`).
- **Building graphs from code:** setting `Grips[i].X/Y` does not update the curve. Write the parameters into a `GH_LooseChunk` and call `graph.Read(chunk)`:
  - Sine: sub-chunk `Equation` with `px`/`py` [0..1];
  - Bezier: `cpx`/`cpy` [0..3];
  - Conic: `Cx`/`Cy`.
- **Sine graph grips** are trough and peak. **Bezier** has 4 control points (end points move vertically only). **Conic** has 1 shoulder grip.
- **Panel text from code:** use real `\r\n` newlines. A literal backslash sequence arrives as one item.
- **Slider values are `Decimal`:** use `str()` / `System.Decimal(v)`. Check `Slider.Type`: `gap`, `spacing` and `Degrees` are **integer** sliders.
- **Slider NickNames:** spacing, Degrees, gap and the site X/Y sliders show labels on the canvas, but their `NickName` reads empty through the API.

**GH Python 3 (Rhino 8)**
- **Plain-script mode works:** inputs are globals, outputs are module-level variables.
- **Set the access type explicitly** (item / list / tree).
- **Input and output names can't be the same.**
- `th.tree_to_list` strips the leading `{0}`. `th.list_to_tree` adds it back.
- `rg.Circle` outputs arrive downstream as `ArcCurve` (`.Radius`, `.Arc.Center`, `.Arc.Plane.ZAxis`).
- `Transform * Point3d/Vector3d` returns new objects. Rotation leaves vectors untranslated.
- `Brick.configuration()` returns `None`: use a short loop.
- **Type hints reset to "ghdoc Object" (geometry arrives as `Guid`):**
  - it happens on every `SetSource`, on adding or removing params, and on components created by LAMCP `add_python_component`;
  - it can pass partial solves and fail a full re-solve;
  - fix: after **every** code or param change, set each input to "No Type Hint" with `param.GetType().GetMethod('SetConverter', Instance|Public|NonPublic).Invoke(param, [goo_hint])`, where `goo_hint` is the `GooConverter` entry of `param.TypeHints`;
  - do it in a **separate** UI call after param changes, because deferred events can reset it again;
  - `TypeHints.Select()` alone does not change the converter.

**Workflow (via LAMCP)**
- Re-read the canvas before every step.
- Edit code with `component.GetType().GetMethod('SetSource').Invoke(component, [code])`, then reapply the type hints and expire.
- Add params with `CreateParameter` + `RegisterInputParam`, then `VariableParameterMaintenance()` + `Params.OnParametersChanged()`. Remove them with `Params.UnregisterInputParameter(p, True)`.
- `_lamcp_run_on_ui` is **not** in the bridge globals. Use `Rhino.RhinoApp.InvokeOnUiThread(System.Action(f))` with `ScheduleSolution`.
- **Wait for `doc.SolutionState != 'Process'`** before reading outputs. Reads during a solve return empty or stale trees.
- **Verify on the real canvas** after emulated calibration. Emulation caught the Graph Mapper still serving the old Sine values.
- The canvas capture fails when the Grasshopper window is minimised.

**Geometry / structure**
- **Check bricks as 3D boxes, not points.** Point distances hid T/R crossings and plan rotation (W·sinθ).
- **Contact share of a T/R crossing is fixed:** W_T·W_R / footprint, 47.5 % (R on T) and 30.8 % (T on R), at any profile.
- **Removing clashing bricks removes support.** Rerun the stacking check after every cull.
- **Curvature:** spacing along the ring underestimates the closeness of inner ends on small rings.

---

## 11. Future explorations: other ways to combine Config 1 and Config 2 in a robotic tower

The aims taken from the design review: (1) volumes that read as **intersecting**, (2) a **continuous solid mass**, (3) bricks that are **redundantly supported** (two or more supports, or ≥ 60 % contact), (4) **top-down robotic placement** with gripper clearance, and (5) fewer bricks. Each option can be tested with the same emulator plus clash and support checks before it touches the canvas.

1. **Bridging bond (lintel courses).**
   - Alternate whole **courses** instead of points within a module: an R course (Config 2, 15.2 tall, radial), then a T course (Config 1, 9.85 tall, tangential) whose bricks **span between two R bricks** below. Then an R course centred on the T joints, and so on. The module is still 9.85 + 15.2 = 25.05.
   - Every T brick sits on two supports. With R spacing s, bearing needs s/2 + 9.85/2 ≤ 16, so s ≤ 22.
   - T courses close into nearly continuous bands that read as mass, and R heads read as teeth crossing the bands.
   - Robot: one orientation per course, so no mixed-orientation clearance within a course.
   - Chain changes: `orient` and `pattern` per course, spacing from the T length, parity per course.
2. **Corbelled rings.**
   - Apply the profile per **course** (every T and R course) instead of per module, with the radius step limited to about 1/3 of the bearing width (≈ 3–5).
   - Each brick then bears about two thirds on the one below, and the silhouette becomes a smooth continuous surface.
   - Needs more courses for the same radius swing, but no count lock: counts stay matched to their rings, so there are no wide gaps.
3. **Double-skin ring with headers** (English or Flemish bond in the round).
   - Two concentric rings of T stretchers (Config 1), tied every other course by R headers (Config 2) spanning both skins. The ring offset is set so a 32 header bears on both.
   - Reads as a thick, solid wall; headers bear on two skins, which makes it very stable.
   - Robot order: outer stretchers, inner stretchers, then headers. More bricks per course, but fewer towers or modules can compensate.
4. **Staggered piers (half-module offset).**
   - Keep the current column logic (one T + one R per module per point), but **offset neighbouring columns by half a module**. Neighbouring bricks then overlap in plan where their height intervals don't overlap.
   - This brings back **intersecting volumes** without clashes, closes the gaps, and lets T bricks overhang onto neighbouring columns for lateral interlock.
   - Chain changes: spacing only needs clearance between bricks whose heights overlap; parity and `module_h` become per column.
5. **Dogtooth / sawtooth courses.**
   - Turn T bricks in plan (30–45°) so they touch corner to corner. The projecting corners give the faceted, intersecting texture while the ring stays continuous; R bricks fill the notches on the next course.
   - Spacing is set by corner contact, not footprint + gap.
   - Robot: place every other brick first, then infill (two passes), or use a gripper narrower than the brick.
6. **Cross-stacked solid piers ("log cabin").**
   - Make each column a dense pier with **two or more** bricks per course (e.g. two T side by side, then two R crossing). Piers touch or overlap neighbouring piers at alternate courses.
   - Every brick bears on two bricks below, and the piers read as solid blocks with intersecting edges.
   - Robot: each pier course is a small, regular pick-and-place pattern.
7. **Helical (continuous) courses.**
   - Replace discrete rings with two interleaved helices (one per config height), so the twist is built in and the robot path is continuous.
   - The most experimental option: support between turns needs the same contact checks.

**Robotic constraints to carry into any option**
- Minimum neighbour clearance equals the gripper finger thickness when bricks are placed top-down at the same height.
- Placement order: no brick may block a later approach.
- Pick and place frames: `Brick.get_pick_frame()`.
- Reach of the robot over the tower height and radius.
- Brick size tolerances (`Measured Brick Dimensions.xlsx`).
- Whether adhesive or mortar is used.

---

## 12. Open items

1. **Design direction after the review (section 8):** choose an alternative from section 11 to prototype.
2. **Curvature clash:** spacing measured along the ring ignores the converging inner ends on small rings (up to 1.1 at r ≈ 43, angle 0°). Measure the spacing at the bricks' inner faces, or add a curvature term.
3. **Guards (deferred), settings that crash Python:**
   - `Modules` = 1;
   - a flat Graph Mapper curve;
   - `Degrees` = 90 with `gap` = 0;
   - a ring with count 0 (Curve Division `DivideByCount`, Rotate Points `len(ps)`);
   - pattern panel values 0, too large, or blank.
4. **`step` formula:** still the sum of the distinct heights. With an unbalanced pattern the two columns differ in height; consider `step = max(module_h)`.
5. **Pattern length must equal the number of sub-levels per module** (Brick Frames maps slot ↔ sub-level).
6. **Floating bricks from the cull between towers:** parked. 0 at the current settings. Handling them would mean removing more bricks, not reintroducing culled ones.
7. **Clash Detection threshold** (largest plan diagonal + gap) is conservative. It could use the actual oriented footprints (`Brick.clash` / `Brick.slack` in `brick_wall.py`).
8. **Frames → assembly rules:** pick and place frames and sequence are left to the user.
9. **Leftovers on the canvas:** Module Information `length` output, Curve Division `params`, the unconnected `rotation` slider, and the native group with its locked Sine Graph Mapper. Retire them once the rebuild is accepted.
10. **COMPAS Draw** takes about 1.6 s per solve. Disable the frames preview when not needed.
11. **The emulator and check scripts** exist only in the bridge session. Save them as a script in the repo if the explorations in section 11 are pursued.
12. **Cosmetic:** empty `NickName` on the spacing, Degrees, gap and site X/Y sliders.
13. **The .gh file is not saved** after the session-2 changes. (Saved by the user as `04_RoboticBricks/Robotic Tower_Lamda.gh`. The native rebuild in section 13 was added after that save.)

---

## 13. Native Grasshopper rebuild (learner version, 2026-10-22)

Built in `Robotic Tower_Lamda.gh` below the "Python rebuild" group. It is a native-component version of the same chain for learners who know Grasshopper. It shares the existing sliders, value lists and panels, and uses faint wires throughout.

- **9 coloured groups**, one per stage. Each has a note explaining its logic and data-tree paths, and a title note gives the legend.
- **GH_Python only where native components can't do the job.** Each sits in a dark-grey sub-group that says why:
  - **Brick Dimensions:** reads `brick_wall.Brick`;
  - **Clash Detection:** a greedy loop, and no looping plugin is installed;
  - **To COMPAS:** compas Frames and Boxes, which the COMPAS plugin has no constructors for.
- **Checked equal to the Python rebuild after every stage:** tower order, `module_h`/`step`/`t`, radii and angles, rings, counts and points per sub-level, twist, bond, kept points, and all 640 frames and boxes (Rhino planes and compas Frames).

| Stage | Native approach |
|---|---|
| 1 Site & Towers | Expressions for the usable grid → Series → Cross Reference (columns vary fastest) → Construct Point → checkerboard mask (`c % 2 = r % 2`) → Cull Pattern |
| 2 Brick Data | Brick Dimensions [Py] → List Item by `pattern − 1`. `module_h`: Dispatch (True/False) → Mass Addition partial sums per column → Weave (0/1). `step`: Create Set → List Item → Mass Addition. `t`: Range |
| 3 Profile | Graph Mapper (Bezier copy) → Bounds → Remap Numbers (radius domain; ±Degrees → Radians) |
| 4 Rings | Series of tower indices (grafted) → Shift List (wrap) → Trim Tree → Construct Point at module heights → Circle |
| 5 Curve Division | Footprint expression (`If(t, …, …)`) → Shift List −1/+1 (no wrap) → Addition → Bounds/Deconstruct Domain (max) → spacing → even count → Trim Tree + Bounds (min per tower). Rings → Duplicate Data + Move (`module_h`) → Divide Curve |
| 6 Rotate Points | `2·Pi/N·shift·Floor(g/m)` → Rotate (points, about the tower axis) and Rotate Vector (tangents) |
| 7 Brick Bond | `j = g % bond` pattern → Cull Pattern |
| 8 Clash Detection | GH_Python (same code as 4.9) |
| 9 Brick Frames | List Item per level (slot s = `g % m`, module k = `Floor(g/m)`) → Rotate Vector (x: + Pi/2 for R; y: x + Pi/2) → Move (−h/2) → Construct Plane → Center Box. To COMPAS [Py] |

**Native pitfalls met**
- **Cross Reference (holistic) varies its first input fastest.** Feed columns first so towers come out row by row, as in Python. The tower order drives each tower's profile shift.
- **Series/Range output paths:** fed from `{0}` they output `{0;0}`. Flatten their outputs to keep trees as `{0;tower;…}`, which `th.tree_to_list` in the Python components needs.
- **Shift List with a grafted or persistent shift, and Duplicate Data, append a trailing index** (`{0;i;0}`). Trim Tree (depth 1, or 2 for counts) restores `{0;tower}`.
- **Trees with different branch counts don't match by path.** Per-level values (angle, slot sizes) are built as `{0;tower}` lists over g, then grafted to `{0;tower;level}`.
- **A newly created Graph Mapper has no container.** Set `mapper.Container = GH_GraphContainer(graph.Duplicate(), x0, x1, y0, y1)`.
- **GH Expression:** use `%` for modulo (`Mod()` doesn't exist), `=` for comparison, `If(c, a, b)`, `Floor`, `Abs`, `Pi`.
- **Path Mapper supports arithmetic** (`{A;B;C*4+D}`). It wasn't needed in the end, because copying rings to sub-levels before division gives `{0;tower;level}` directly.
- **Preview:** only the site rectangle and the native bricks preview. The Python rebuild still previews its own bricks, so both overlap in the viewport.
