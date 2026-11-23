# Design workflow (group_2)

This file describes how the work in `facade_form.gh` and `facade_texture_mike.gh` fits into `design_weijiun.gh`. It is written to be read at the start of a new session, by people and by models.

- It is a plan and a description. None of the three .gh files were changed to write it.
- It was read from the open canvases on 2026-11-19, after the unused parts of `design_weijiun.gh` were deleted.
- For the details behind the facade components, see `facade_form_and_infill.md` (fold, form, infill) and `facade_development.md` (PIXEL pattern, first fold versions).

Each stage has a title of no more than four words and a short description (under 75 words) for every component in it, so the stages can go onto slides directly.

## 1. What each file does

| File | Role | Status |
|---|---|---|
| `design_weijiun.gh` | The overall file: Y mesh → Y blocks → non-planar print chain → saved JSON. It also has an early facade test (`1f FACADE TEXTURE (test)`) that is not wired to the print chain. | Main file |
| `facade_form.gh` | Changes the **shape** of a facade wall: a cached slicer, two pattern options (fold or form) and infill ribs. | Final chain tagged [S1c]–[S4] |
| `facade_texture_mike.gh` | Changes the **texture** of a facade wall: gives every point an extruder index (speed) from a window pattern. | Pattern options. The plug-in group "3 DESIGN HERE" is disabled. |

## 2. How the facade files plug in

### Data flow after integration

```
Cluster (Count, Seed) -> Mesh -> Y blocks
   Y blocks.facade_component -> wall pts (cached)            -> external / inner / other
   external, inner           -> facade fold (all) | facade form (clean, live)   (facade_option, Stream Filter)
   pattern + wall pts        -> facade infill (v3)           -> infilled (external path with ribs)
   infilled                  -> point index (external)       -> pt_index   (speed pattern)
   other                     -> point index (other)          -> pt_index
   infilled, inner, other + indices -> merge layers          -> layers / index / vectors
   -> design layers / point class / tool vectors (non planar)   <- the hand-off (was Y blocks)
   -> add tail (non planar) -> printpath (non planar) -> place on bed -> save
   -> data/out_printpoints_weijiun_nonplanar.json  (read by send_to_robot_test.py)
```

### What replaces what in `design_weijiun.gh`

| In `design_weijiun.gh` now | Comes from | Change |
|---|---|---|
| `wall pts` | `wall pts (cached)` (facade_form) | Same slicing, plus a cache. Input stays `Y blocks.facade_component`. |
| `facade texture` | `facade form (clean, live)` + `facade fold (all)` + `facade_option` / Stream Filter (facade_form) | `facade texture` uses the same algorithm as `facade form`. The clean copy gives the same output, and the fold is the second option. |
| (nothing) | `facade infill (v3)` + `infill` toggle + `rib_count` (facade_form) | New, between the pattern and merge layers. |
| (nothing) | one `point index (external)` pattern + its sliders, `point index (other)` + Value List (facade_texture_mike) | New, reads `facade infill (v3).infilled`. |
| `merge layers` (index inputs empty) | the same `merge layers` | The script is identical in all three files. Wire `external_index` and `other_index`. |
| `design layers` / `point class` / `tool vectors (non planar)` ← `Y blocks` | ← `merge layers.layers / index / vectors` | The only rewire into the print chain. |
| `Y blocks` (optional) | `Y blocks (lean, cached)` (facade_form) | Faster, with the same print outputs. It has no `bridge_no` input or `bridge_component` output, and it adds an `out` output. |

Do not bring over from `facade_texture_mike.gh`: its `wall pts` (an older version that needs vertex colours) or the `12 walls (internalised)` mesh and `Item` slider. These were only test inputs. Use `Y blocks.facade_component` → `wall pts (cached)` instead.

### Formats at the hand-off points

- **wall pts outputs** (`external`, `inner`, `other`): `[layer][Point3d]`, on the bed, in print order inside each group.
- **pattern / infill outputs** (`folded`, `textured`, `infilled`): the same structure as `external`. The point count can change: the fold drops points that would loop, and the infill adds ribs.
- **point index `pt_index`**: `[layer][int]`, one value per point, in the same order as the points. 1 = off, 2 = DO2 (1 mm/s extrusion), 3 = DO3 (7 mm/s).
- **merge layers outputs**: the same format as `Y blocks.layers / index / vectors`, so `add tail (non planar)` takes either.
  - It matches indices to points **by position**. A missing value or a short branch becomes 3.

## 3. Workflow stages (slide outline)

### Stage 1: Y Mesh Generation
- **Number Sliders (Count, Seed)**: Choose the variant of the Y shape the cluster builds. Count is 3 and Seed is 5 at the moment. Changing either changes the whole shell, so every later stage solves again.
- **Cluster → Mesh**: Builds the Y mesh, the mid surface of the shell. The Mesh parameter passes it to `Y blocks` as `y_mesh`.

### Stage 2: Y Blocks Shell
- **Y blocks sliders (18)**: Set the model size (600 mm), the shell and facade thickness, layer height (1.3 mm), bead width (3 mm), point spacing, cable holes, lap joints, tongue, the 1:20 scale and the ceiling and railing heights. `print_block` picks the block to slice. `facade_no` picks the railing wall for the facade chain.
- **Y blocks**: Scales and smooths the Y mesh, gives it thickness and cuts it into 18 shell blocks (0–17) and 12 railing walls (18–29). It slices `print_block` into non-planar layers, a fan of planes. Outputs: `layers`, `index` and `vectors` for printing, `facade_component` (wall `facade_no`) for the facade chain, and meshes for preview.
- **Y blocks (lean, cached)** (optional, from facade_form): Gives the same print outputs about 250 lines shorter, and caches the blocks, so changing `print_block` only slices again. It drops `bridge_no` and `bridge_component`. Turn on its `out` output to read the info text.
- **Mesh previews, bead preview, Point List**: Show the chosen block, the facade wall, the bridge block, the block on the bed and all blocks in clear PETG colour. The Point List tags every block centre with its number, which helps you pick `print_block`.

### Stage 3: Model Checks
- **cable lines → Pipe → previews**: Give a quick preview of the assembled bridge. They slice a few sample layers of every block, draw the cable runs through the bridge blocks as pipes and show sample print paths. Cached, so the preview only runs again when Y blocks or a design input changes.
- **scale person**: Places a simple standing figure, scaled 1:`scale_1_to`, on top of one shell block, so presentations show the human scale of the canopy and railing.
- **filament weight**: Estimates grams and extruded length for the sliced block from a fit to weighed prints, plus a total for all 30 blocks. It reads `Y blocks.layers`, so it measures the shell block, not the facade path.

### Stage 4: Facade Wall Slicing
- **wall pts (cached)** (replaces `wall pts`): Slices the railing wall from `Y blocks.facade_component` lying down, with one cross section per layer. It splits every layer into `external` (facade face, red), `inner` (curve facing the deck, blue) and `other` (tongue, foot and end faces, grey). Fixed settings: 1.3 mm layers, 3 mm bead, 2.5 mm points. It only slices again when the wall mesh changes.

### Stage 5: Facade Form Options
- **facade fold (all)**: Folds the facade face outward along the layer plane. `fold_count` and `fold_depth_mm` set the folds. `blend` goes from sawtooth (0) to sine (1). `flip` reverses the sawtooth. `across` sets the crease direction. `line_amp`, `line_waves` and `line_phase` swing the fold lines in a wave. Run ends stay fixed.
- **facade form (clean, live)** (replaces `facade texture`): Cuts the external path into units with unit lines. On a line the path stays touching the inner wall, and between lines it bulges out (`bulge_mm`). `pitch_mm` sets the unit size. `wave_count` and `wave_amp` swing the lines over the wall length, which makes wavy horizontal ribs on the railing.
- **facade_option + Stream Filter**: A design-option switch. 0 sends the fold and 1 sends the form to the infill, so both patterns stay live and can be compared without rewiring.

### Stage 6: Facade Infill Ribs
- **facade infill (v3)**: Adds U-shaped ribs from the facade face to one bead short of the inner curve. They sit in the creases of any pattern, found from how far each point was pushed. Ribs are skipped where the gap is under 6 mm or the foot or tongue is nearer. The inner curve stays clean.
- **infill toggle, rib_count**: `infill` False switches the ribs off. Do not disable the toggle, because a disabled toggle sends nothing. `rib_count` adds evenly spaced ribs that stack into webs, which an along-Z fold needs.

### Stage 7: Extrusion Speed Pattern
- **point index (external), pattern options**: Give every facade point an extruder index: solid = 3 (7 mm/s) and window = 2 (1 mm/s, less material). The options are zig-zag (windows swing back and forth), slash (they shift one point per layer) and pixel (they step half a window every `shift_step` layers). Windows join the layer below into cells. Each option comes with or without a gradient.
- **pattern sliders and mirror toggle**: `w_count` = windows per layer, `shift_step` = layers per shift, `w_share` = window share of the interval. On the gradient versions, `int_step` changes the window interval per layer from the middle layer outward, and `mirror` makes that change symmetric. The `pts_1` / `pts_2` previews show the solid and window points.
- **point index (cyan logic)**: The PIXEL pattern rewritten to match the cyan grid test: one window width for all layers, so the diagonals never jump back, a minimum solid stretch and the cyan shift direction. It warns when layers have different point counts, which it needs to be equal.
- **point index (other) + Value List**: Gives every tongue, foot and end-face point one index, picked in the Value List, for example 3 for full extrusion. The points pass through unchanged. Inner points need no component, because an empty input becomes 3.

### Stage 8: Merge Into Layers
- **merge layers**: Joins `infilled` (external), `inner` and `other` back into one closed loop per layer. It starts at the first `other` point and continues with the nearest run. Each point keeps its extruder index. It also builds the tool vectors: the layer-plane normal, pointing down to the layer below, with a length equal to the layer height.
- **PolyLine, bead preview**: Draw each merged layer as a polyline in clear PETG colour, so you can check the facade shape, ribs and seams before printing.

### Stage 9: Print Chain Hand-off
- **design layers / point class / tool vectors (non planar)**: Three parameters at the entry of the print chain. Wire them from `merge layers.layers / index / vectors` to print a facade wall. Today they come from `Y blocks`, which prints the shell block `print_block`. This is the only rewire into the print chain.

### Stage 10: Add Tail Point
- **add tail (non planar)**: Flattens the layers into one print list. It adds a lead-in tail point F mm out from the first point, square to the first path and outside the part. It also outputs the point class, tool vector and layer number of every point.
- **F and Item panels**: F = 100 sets the tail length in mm. Item = 2 gives the tail point the slow DO2 extruder index.

### Stage 11: Build Print Path
- **printpath (non planar)**: Turns every point into a PrintPoint (`src/print_class_02.py`). The tool axis follows the tool vector, so the nozzle tilts with the layer. Speed comes from the class (Genes) and rises on thinner layers, up to 2×. Safety points are added before and after. The summary panel reports points, layers, layer heights, speeds and tilt.
- **Genes, blend_radius, safety_distance, first_layer_lift**: Genes holds the robot speeds: the first value for class 3 and the second for class 2. The blend radius is 1 mm and the safety distance 100 mm. `first_layer_lift` (0.7 mm) raises the whole path, so the first layer is not pressed into the bed.

### Stage 12: Locate Print Bed
- **bed corner panels, Merge, Point List**: Four measured bed corners in robot base coordinates (mm). The Merge and Point List show them in the viewport, so you can check the corners before placing the part.
- **printbed_position, Pt, Cluster**: The 4 Point Surface builds the bed surface from the corners. Pt (u 0.5, v 0.5) picks the bed centre. The Cluster turns the object by the angle slider (180°) and outputs the bed plane.

### Stage 13: Place and Save
- **place on bed**: Moves the whole print path from world XY onto the bed plane, which puts it in robot base coordinates. The original path is left unchanged. The summary gives the bed origin and the z range.
- **save button, out_path panel**: Pressing save writes the placed path to `data/out_printpoints_weijiun_nonplanar.json`, the JSON that `send_to_robot_test.py` reads. The status panel shows how many printpoints were saved.

### Stage 14: Simulate Before Printing
- **UR5 Path Solver, UR5 Robot Pose** (disabled): Check reach, wrist flips, singularities and collisions of the placed path with the tool mesh. They then show the robot pose at Index, or play the path, before the robot moves.
- **extrusion preview + bead preview** (disabled): Show the bead width from each point's extruder index (the line width sliders for DO2 and DO3). Red marks beads thinner than the layer, which may not bond. Use it to check the speed pattern.

## 4. Check before you integrate

1. **Slider values differ between the files.** Choose them before you rewire.

   | Slider | `design_weijiun.gh` | `facade_form.gh` |
   |---|---|---|
   | `facade_thickness_mm` | 6 | 16 |
   | `facade_no` | 3 | 7 |
   | `print_block` | 16 | 23 |

   At 6 mm the infill adds 0 ribs, and at 16 mm it adds about 500.
2. **The speed pattern runs after the infill.** This keeps the indices in step with the printed points. Two known limits follow:
   - Rib points get whatever index the pattern gives them.
   - PIXEL expects every layer to have the same point count, which the wall and the infill do not give, so its windows are counted in points, not mm.
3. **`filament weight` and `Point List` still read Y blocks**, so they describe the shell block, not the facade wall.
4. **`Y blocks (lean, cached)` has no `bridge_component`.** Keep the original Y blocks if you need the bridge block preview. `wall pts (cached)` works with either.
5. **Robot safety.** The ribs and the slow windows are extruder-on moves inside every layer. Check the saved path in simulation (Stage 14) and as a dry run (`SEND = False`) before the first print. Keep travel moves at index 1.

## 5. Other components still on the canvas

These are on the lower part of `design_weijiun.gh`, far from the chain above, and are not connected to it. Some have empty inputs: the `interpolated column` shape sliders, the first `save`'s `printpath`, and `Face Boundaries`.
- `slice brep` with its sliders and Brep parameter: classic slicing of a Brep.
- `interpolated column` with its sliders: an earlier column design.
- `Python 3 Script` (column class) → PolyLine → Loft → Preview: a column preview.
- `save` in "DISPLAY: check before you print": the old save to `data/out_printpoints.json`.
- `Face Boundaries` and loose scribbles from the course template.
