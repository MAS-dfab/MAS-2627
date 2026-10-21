# GH to Python Conversion – Geometry

**File:** `04_RoboticBricks/Michael/Robotic Tower.gh`
**Date:** 2026-10-21
**Goal:** Understand the existing native-Grasshopper tower definition (rings → divided by projected brick length), fix its problems, then rebuild it stage by stage as lean GH Python 3 components that produce the same results. After that, add two new components: one that twists each tower's division points (Rotate Points) and one that culls clashing points between towers (Cull Points).

The original components are all still on the canvas for comparison and revert. The Python rebuild is in the blue **"Python rebuild"** group below the original definition.

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

### What each Cluster Heights output actually means
With brick heights a and b, `module_h = [0, ½|a−b|, ½(a+b), max(a,b)]` and `step = a+b`.

These four values are the **bottom and top faces of each brick, with both bricks centred on a shared mid-plane**. The outer pair belongs to the taller brick and the inner pair to the shorter one. Because the formula uses `abs()` and `max()`, it doesn't depend on order: swapping the configs gives the same levels.

### Count formula
`((c/p)\2)*2` with `p = ½·(L·cosθ + gap)` works out to `2 · floor(c / (L·cosθ + gap))`. That's always even, with **two points per brick slot** (half-length spacing). The user did this on purpose so that alternating points can later be culled per row to make a brick bond.

---

## 2. Problems found in the original definition (all fixed by the user)

1. **The projected length used the ring radius instead of the brick length.** x in `½·(x·cos(y)+gap)` was wired from the radius ReMap. It's now wired from Brick Dimensions (Config 1) `length`.
2. **Division counts were paired with the wrong rings.** The circles used *shifted* radii (9 branches × 14), but the projected length used *unshifted* radii and angles (one flat list of 14). Grasshopper paired them by level index, so each tower's ring was divided using another level's radius and angle. Fixed by adding a second Shift List that shifts the angles by the same per-tower values.
3. **The shift expression didn't do what it seemed to.** In `int((x%(z\2))*max(x))`, `max()` of a single item is just that item, so the shift was `(i mod 4)·i`, and one input wasn't used. It was replaced with `x%z`, which gives shifts of 0–8.
4. **Two sliders were both called `min_radius`.** The Diagrid one was renamed `offset`.
5. **A stray `Format("{0}, {1}", x, y)` expression with no inputs** was deleted.

Left alone on purpose: the panel-only outputs (the 56 sub-levels from Series → Flip only fed a panel). The cull component now uses `module_h` to move points to those sub-levels.

---

## 3. User preferences and working rules (apply to future components)

- **Plain-script GH Python 3:** no `Script_Instance` class and no helper defs. Inputs are globals and outputs are assigned variables. Use a simple list comprehension where one will do. Don't over-engineer.
- **No hard-coded design values.** Every slider, value list and Graph Mapper stays **outside** the component as an editable input. A Graph Mapper is treated like a slider.
- **Faint wires** on every new input.
- **Matched data-tree paths.** Convert between nested lists and trees with `ghpythonlib.treehelpers` (`list_to_tree` / `tree_to_list`).
- **Never delete the user's existing components.** Build alongside them for comparison and revert.
- **One component at a time,** with an approval check-back before the next. Ask clarifying questions before implementing.
- **Formulas must not be specific to Config 1 and 2.** Logic has to work for any number of configs.
- The user renames components and outputs after they're built. Always re-read the canvas before referring to names.
- Converting to compas.geometry (frames etc.) is left to the user. Rhino.Geometry is fine for display geometry.

---

## 4. The Python rebuild

Final names (after the user's renames) and how data flows:

```
X/Y Size, offset, spacing ─► Diagrid and Site ─► points ───────────────────────────────┐
configs (Config 1, Config 2), pattern, Modules ─► Module Information                    │
        ├─► t ─► Graph (new Graph Mapper) ─► Radii and Rotations ─► radii, angles ─► Rings ─► rings, ring_angles
        ├─► step ─────────────────────────────────────────────────────────────────┘          │
        ├─► length ──────────────────────────────────────────────────► Curve Division ◄──────┤
        │                                                     points, tangents │             │
        │                                         rotation slider ─► Rotate Points ◄── rings ┤
        │                                                rot_points, rot_tangents │          │
        └─► lengths, widths, module_h ──────────────────────────────► Cull Points ◄── rings ─┘
gap slider ─► Curve Division, Cull Points
```

### 4.1 Diagrid and Site (stage 1)
Inputs: `x_bound`, `y_bound`, `offset`, `spacing` (item). Outputs: `site`, `points` (one flat list, one point per tower).
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
Checked: identical to `Diagrid.pts` (9 points).

### 4.2 Module Information (stage 2, generalised with a pattern)
Inputs:
- `configs` (list): both Config value lists wired in order.
- `pattern` (list): a Panel `1,2,2,1` holding 1-based positions in `configs`.
- `modules` (item).

Outputs:
- `length`: the first slot's brick length, used by Curve Division.
- `lengths`, `widths`: one value per pattern slot.
- `module_h`, `step`, `levels` (56 values).
- `t`: 0…1, one value per module, for the Graph Mapper.
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

# Distinct bricks centred on a shared mid-plane: their bottom/top faces are the sub-levels
used = [bricks[i] for i in sorted({int(p) - 1 for p in pattern})]
top = max(b.height for b in used)
module_h = sorted({(top + s * b.height) / 2 for b in used for s in (-1, 1)})
step = sum(b.height for b in used)

# All sub-levels, module by module
n = int(modules)
levels = [m * step + h for m in range(n) for h in module_h]

# Normalised level parameters (0..1) for the Graph Mapper
t = [i / (n - 1) for i in range(n)]
```
Checked: `module_h` = [0, 2.675, 12.525, 15.2] and `step` = 25.05, matching Cluster Heights. `levels` matches Flip (56 values) and `t` matches Range (14 values).

### 4.3 Graph (new Graph Mapper)
A duplicate of the original **Sine** graph, fed by `Module Information.t`. Its output matches the original mapper exactly. **It is independent of the original:** editing one changes only its own chain.

### 4.4 Radii and Rotations (stage 3)
Inputs: `graph` (list), `min_radius`, `factor`, `degrees`. Outputs: `radii`, `angles` (14 each, unshifted).
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
Checked: matches both ReMap outputs exactly.

### 4.5 Rings (stage 4)
Inputs: `points`, `radii`, `angles` (list), `step` (item). Outputs: `rings`, `ring_angles`, nested `[tower][level]` with paths `{0;tower}`.
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
Checked: all 126 circles (centre, Z, radius) match the original Circle output, and the angles match the angle Shift List.

### 4.6 Curve Division (stage 5)
Inputs: `rings`, `ring_angles` (tree), `length`, `gap` (item). Outputs: `points`, `tangents`, `params`, nested `[tower][level][point]` with paths `{0;tower;level}`.
```python
import math
import ghpythonlib.treehelpers as th

ring_list = th.tree_to_list(rings)
angle_list = th.tree_to_list(ring_angles)

# Two division points per projected brick length (+ gap), rounded down to an even count
counts = [
    [int(c.GetLength() / (0.5 * (length * math.cos(a) + gap)) // 2 * 2) for c, a in zip(cs, aa)]
    for cs, aa in zip(ring_list, angle_list)
]
t = [[list(c.DivideByCount(n, True)) for c, n in zip(cs, ns)] for cs, ns in zip(ring_list, counts)]

points = th.list_to_tree([[[c.PointAt(x) for x in ts] for c, ts in zip(cs, tt)] for cs, tt in zip(ring_list, t)])
tangents = th.list_to_tree([[[c.TangentAt(x) for x in ts] for c, ts in zip(cs, tt)] for cs, tt in zip(ring_list, t)])
params = th.list_to_tree(t)
```
Checked: at Modules = 14, all 3,132 points, tangents and parameters matched the original Divide Curve.

> **Later finding:** at Modules = 8, 18 of 72 rings differ (e.g. 22 vs 24 points, 28 vs 30). This is a rounding difference, not a Python error. GH's `\` rounds its left operand to the nearest integer *before* dividing (VB-style), so the original is really `2·(round(c/p) ÷ 2)`, while Python uses `2·floor(c/p ÷ 2)`. The match at Modules = 14 was a coincidence. See open item 1.

### 4.7 Rotate Points (new: twist per tower)
Sits between Curve Division and Cull Points.
- **Inputs:** `rings` (tree, from Rings), `points` and `tangents` (tree, from Curve Division), `rotation` (item). `rotation` comes from a new slider, 0–90°, whole degrees, default 0.
- **Outputs:** `rot_points`, `rot_tangents`, same paths as the input (`{0;tower;level}`). These now feed Cull Points instead of the Curve Division outputs.

Circle k of each tower turns `k × rotation / (circles per tower)` about its own axis (the ring plane's Z axis through its centre). Tangents get the same transform.
```python
import math
import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

ring_list = th.tree_to_list(rings)
pt_list = th.tree_to_list(points)
tan_list = th.tree_to_list(tangents)

# Twist: each circle turns rotation / (circles per tower) further than the one below, about its own axis
xforms = [
    [rg.Transform.Rotation(math.radians(rotation / len(cs) * k), c.Arc.Plane.ZAxis, c.Arc.Center) for k, c in enumerate(cs)]
    for cs in ring_list
]

rot_points = th.list_to_tree([[[x * p for p in ps] for x, ps in zip(xs, pss)] for xs, pss in zip(xforms, pt_list)])
rot_tangents = th.list_to_tree([[[x * v for v in vs] for x, vs in zip(xs, vss)] for xs, vss in zip(xforms, tan_list)])
```
Checked:
- At 0°, the output is identical to Curve Division.
- At 90° with 8 circles, levels 0–7 turn exactly 0, 11.25, 22.5 … 78.75°, and the tangents turn by the same angles. Radius and Z are unchanged, and the tangents are still tangent to their circle.
- After rotation, Cull Points still clears the threshold (closest pair on different towers 38.46, threshold 38.43).

### 4.8 Cull Points (new: clash culling between towers)
Inputs:
- `rings` (tree), plus `points` and `tangents` (tree, now from Rotate Points)
- `lengths`, `widths`, `module_h` (list)
- `gap` (item)

Outputs: `kept_points`, `kept_tangents`, nested `[tower][sub-level]` with paths `{0;tower;sub-level}` (9 × 56).
```python
import math
import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th

ring_list = th.tree_to_list(rings)
pt_list = th.tree_to_list(points)
tan_list = th.tree_to_list(tangents)
towers, levels = len(ring_list), len(ring_list[0])

# Clearance between towers: largest brick plan diagonal in the pattern + gap
threshold = max(math.hypot(l, w) for l, w in zip(lengths, widths)) + gap

# Per level, larger rings win: go from largest to smallest radius (ties keep tower order)
# and keep a point only if it clears every point already kept on other rings
keep = [[None] * levels for _ in range(towers)]
for k in range(levels):
    kept = []
    for i in sorted(range(towers), key=lambda i: -ring_list[i][k].Radius):
        keep[i][k] = [all(p.DistanceTo(q) >= threshold for q in kept) for p in pt_list[i][k]]
        kept += [p for p, ok in zip(pt_list[i][k], keep[i][k]) if ok]

# Copy the kept points and tangents to every sub-level of their module
kept_points = th.list_to_tree([
    [[p + rg.Vector3d(0, 0, h) for p, ok in zip(pt_list[i][k], keep[i][k]) if ok] for k in range(levels) for h in module_h]
    for i in range(towers)
])
kept_tangents = th.list_to_tree([
    [[v for v, ok in zip(tan_list[i][k], keep[i][k]) if ok] for k in range(levels) for h in module_h]
    for i in range(towers)
])
```
Checked (at Modules = 14, factor 2.107, before Rotate Points existed):
- Threshold is 38.43 (diagonal 35.43 + gap 3). The closest pair of kept points on different towers is 38.68 apart.
- 1,966 of 3,132 points are kept per module level, which becomes 7,864 after copying to the sub-levels.
- The largest ring at each level keeps all of its points.
- Every sub-level has the same points, offset exactly by `module_h`, and the tangents stay in step with the points.

---

## 5. Decisions (and why)

| Decision | Reason |
|---|---|
| One Python component per stage (1–5); stage 0 not converted | Matches the outlined stages, with nothing extra. |
| Wire the new components to the **existing** sliders and value lists | Old and new chains run on identical inputs, so they can be compared directly. |
| Graph Mapper kept as an external input; `t` comes from Module Information (option a) | The profile stays editable by hand, and the Range logic moves into Python. |
| Diagrid and Site outputs a flat list; Rings builds `[tower][level]` | No grafting needed. Rings and Curve Division share consistent `treehelpers` paths, replacing the old mix of `{0;i}`, `{i}` and `{0;k}`. |
| Rhino.Geometry for the rings | Displays directly in GH. Converting to compas is left to the user. |
| Config logic replaced by a `pattern` input (1-based positions in `configs`) | Removes the formulas that only worked for Config 1 and 2, and supports any number of configs or pattern length. |
| Cull compares only **other rings at the same module level** | Same-ring spacing is already set by the cos/half-length division. Adjacent levels are only 25.05 apart vertically, which is less than the threshold, so including them would cull against the levels above and below. |
| Threshold = **max plan diagonal over the pattern + gap** | A safe clearance for any relative rotation of neighbouring bricks, taken from the brick dimensions rather than a typed number. |
| **Larger ring wins**, processed largest → smallest radius and compared against *kept* points only | User's choice. The largest ring at each level is never culled, and ties fall back to tower order. |
| Cull at the module level first, then copy to the sub-levels | User's rule: the same points are culled on every sub-level of a module. |
| Alternating every-other-point removal **not** included | The user plans to do it separately to create the brick bond. |
| Rotate Points sits **between Curve Division and Cull Points** | The cull has to test the twisted positions, not the unrotated ones. |
| Twist step = `rotation / (circles per tower)`, cumulative per circle | User's specification: "for 10 circles at 90°, each circle rotates 90/10". The top circle therefore reaches `(n−1)/n × rotation`. |
| Rotation slider 0–90°, whole degrees, default 0 | At 0 the chain behaves exactly as it did before Rotate Points existed. |
| Outstanding check findings left for the user to fix | The user asked for a check only; fixes will be made manually. |

---

## 6. Pitfalls and lessons learned

**Grasshopper**
- **Hidden input expressions:** Range `N` had `x-1` set on the input itself, so it isn't visible on the canvas. Always inspect input expressions when reverse-engineering.
- **A clean solve isn't a correct solve:** the radius/angle mismatch raised no errors. Longest-list matching paired a flat list of 14 with 9 branches of 14 without complaint. Check data counts and paths, not just warnings.
- **`max(x)` in an Expression with a single item** just returns that item.
- **Integer division** in GH Expressions is `\` (as in `((c/p)\2)*2`). Like VB, it **rounds the left operand to the nearest integer before dividing**, so `23.52 \ 2` gives 12, not 11. Python's `//` floors instead. A one-off match between the two can be a coincidence, so **re-verify after changing inputs** (here, Modules 14 → 8 exposed the difference).
- **Re-check equivalence whenever sliders change.** The user changed Modules and factor between steps, and the branch count went from 126 to 72. Always read slider values before interpreting counts.
- **Flatten flags on outputs** (Diagrid `pts` was flattened) and **graft flags on inputs** (pDecon, Shift `S`) change paths silently. Look for them.
- **A Panel used as a data relay** ("Step between Modules" → Series) works, but it converts numbers to text and back.
- **Duplicate slider names** (`min_radius` twice) make it easy to wire the wrong one.
- **Cluster Heights doesn't depend on order:** `1,2,2,1` and `2,1,1,2` give the same sub-levels. The outer faces always belong to the *taller* brick, not to Config 1. This matters later if frames per sub-level are expected to carry a specific config.
- **A Graph Mapper needs sampled input values;** it can't be "read" as a function by a Python component. Feed it `t` and pass its output in.
- A duplicated Graph Mapper **doesn't stay linked** to the original. Keep this in mind when comparing the two chains.

**GH Python 3 (Rhino 8)**
- **Plain-script mode works:** with no `Script_Instance`, inputs are globals and outputs are module-level variables.
- **Set the access type explicitly:** item / list / tree. A list fed into an item input makes the script run once per item. Points, radii and angles need list access; rings, points and tangents need tree access.
- **Input and output names can't be the same,** hence `ring_angles` and `kept_points` / `kept_tangents`.
- `th.tree_to_list` strips the leading `{0}` by default, so `{0;i;k}` becomes `[i][k]`. `th.list_to_tree` puts a `{0;…}` prefix back.
- `rg.Circle` outputs arrive downstream as **`ArcCurve`**. Use `.Radius`, `.GetLength()`, `.DivideByCount()`.
- Panel values come in as **strings**, so use `int(p)` for the pattern.
- `Transform * Point3d` and `Transform * Vector3d` work directly in Python and return new objects. That avoids the in-place `.Transform()` on struct copies. A rotation transform applied to a vector rotates it without translating it, so tangents stay correct.
- Use `ArcCurve.Arc.Center` and `ArcCurve.Arc.Plane.ZAxis` for a ring's axis.
- `Brick.configuration()` returns `None`, so it can't go in a comprehension. A short loop is clearer.
- Value-list order in a multi-source list input follows the order the wires were connected (Config 1 then Config 2).

**Workflow (via LAMCP)**
- Re-read the canvas before every step. The user renames components and outputs.
- To edit a Python 3 component's code: `component.GetType().GetMethod('SetSource').Invoke(component, [code])`, then expire it and schedule a solution.
- To add or remove params: `CreateParameter` + `RegisterInputParam` / `RegisterOutputParam`, then `VariableParameterMaintenance()` and `Params.OnParametersChanged()`.
- Make canvas changes on the UI thread (`_lamcp_run_on_ui`) and use `ScheduleSolution`, never a synchronous solve.
- Verify every component against its native counterpart, value by value and path by path, before moving on.

---

## 7. Full check after adding Rotate Points

Settings at the time: Modules 8, factor 1.601, Config 1 / Config 2, pattern 1,2,2,1, gap 3, Degrees 30. The rotation slider was tested at 0° and 90°, then set back to 0.

- **Runtime messages:** none on any object in the canvas.
- **Solve times:**

  | Component | Time |
  |---|---|
  | Diagrid and Site | 56 ms |
  | Module Information | 15 ms |
  | Radii and Rotations | 40 ms |
  | Rings | 64 ms |
  | Curve Division | 108 ms |
  | Rotate Points | 61 ms |
  | Cull Points | 345 ms |

  The whole Python chain takes about 0.7 s.
- **Still identical to the originals:** tower points, `module_h`, `step`, `levels`, `t`, Graph Mapper output, radii, angles, all rings. Rotate Points at 0° is identical to Curve Division.
- **Not identical:** Curve Division vs Divide Curve. 18 of 72 rings differ, because of GH's `\` rounding (see 4.6 and the pitfalls).

---

## 8. Open items (to be solved manually by the user)

1. **Division rounding mismatch:** the original `((c/p)\2)*2` rounds c/p *up* past .5 (23.52 → 24 points). Python floors it (→ 22). Rounding up puts the points closer than half the projected brick length, so neighbouring bricks on a ring could overlap. The Python version is probably the intended one. Pick one and align the other chain.
2. **The top circle doesn't reach the full rotation:** with n circles the top one turns `(n−1)/n × rotation` (78.75° of 90° with 8). Divide by `n − 1` if the top should reach the slider value.
3. **Twist only changes between modules:** rotation is applied per module ring, and Cull Points copies those points to all sub-levels, so the 4 sub-levels of a module share one rotation.
4. **Settings that crash Python but not the native components:**
   - **Modules = 1:** `t` divides by `n − 1 = 0` (Module Information).
   - **A flat Graph Mapper curve:** `g_max − g_min = 0` (Radii and Rotations).
   - **Degrees = 90 with gap = 0:** the projected length is 0, so dividing by it fails (Curve Division).
   - **A ring smaller than one projected brick:** the count becomes 0, `DivideByCount(0)` returns `None`, and `list(None)` fails (Curve Division).
5. **Pattern panel input isn't checked:**
   - `0` silently means the *last* config (index −1 wraps around).
   - A number larger than the number of configs gives an IndexError.
   - A blank line gives a ValueError.
6. **Two configs set to the same orientation** give 2 sub-levels instead of the original's 4 (with duplicates), so Cull Points copies to only 2 sub-levels.
7. **Curve Division uses only the first slot's brick `length`.** Other configs in the pattern (e.g. Config 3, length 15.2) don't affect the spacing.
8. **Alternating cull per row** (every other half-spacing point, offset between rows) to make the brick bond.
9. **Convert to compas.geometry** (points + tangents → `Frame`s).
10. **Slot → config mapping per sub-level:** the sub-level heights don't depend on pattern order (see pitfalls). Define a rule if frames need a specific config per sub-level.
11. **The cull is conservative:** clash checks include half-spacing points that the alternating cull will remove later. Consider reordering, or checking only brick-centre points, once the alternation is in place.
12. **Two Graph Mappers now exist.** Edit both, or retire the original chain once the Python rebuild is accepted.
13. **Cosmetic:** the gap, Degrees, spacing and site X/Y sliders have no nicknames.
