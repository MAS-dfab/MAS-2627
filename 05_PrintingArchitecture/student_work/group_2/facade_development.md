# Facade development

What we built in `facade_texture_mike.gh` and `facade_form.gh` (group_2): the decisions, what we learned, and the pitfalls. The scripts follow the red group's style: plain functions, short comments that say what each step is for, Python 3.9.

## Components at a glance

| File | Component | What it does | Status |
|---|---|---|---|
| `facade_texture_mike.gh` | `point index (external) PIXEL cyan` | PIXEL pattern rewritten to follow the cyan grid script's logic | Beside the original PIXEL module, nothing downstream uses it |
| `facade_form.gh` | `facade form (clean)` | Lighter, clearer copy of `facade form`, same output | Beside the original |
| `facade_form.gh` | `facade fold` | Folds whose creases run along mesh Z | Own sliders, nothing downstream uses it |
| `facade_form.gh` | `facade fold (across)` | Folds whose creases run across the layers | Own sliders, nothing downstream uses it |
| `facade_form.gh` | `facade fold (wave)` | `facade fold` with sine-shaped fold lines | Own sliders, nothing downstream uses it |
| `facade_form.gh` | `facade fold (across, wave)` | `facade fold (across)` with sine-shaped fold lines | Own sliders, nothing downstream uses it |

The original components were not changed. Every new component was checked against the existing output or against its formula before it went on the canvas.

---

## 1. PIXEL vs the cyan grid script (`facade_texture_mike.gh`)

**Starting point:** the cyan group is a flat test grid of 100 rows × 51 points with even spacing. It sets windows (points that don't extrude) per layer: the spacing between windows changes by `interval_step` per layer, and every `shift_step` layers the windows move sideways by half a window. A window is also stretched to cover where it sat on the layer below, which joins the windows into diagonal cells. The red PIXEL module copies this onto the wall's points (143 rows, shrinking from 71 to 58 points).

**What we found wrong with the old PIXEL module:**
1. The window width was recalculated every layer, as `int(w_share × interval)`. Because the shift is `(layer // shift_step) × width / 2`, the shift went backwards each time the width dropped by a whole step. That happened at 8 layers, by up to 10 points, and left kinks in the diagonals.
2. Joining a window to the one below assumes the width stays the same and the spacing changes slowly. With the per-layer width, the joins smeared at those kinks.
3. The pattern counts points, but the wall's points are unevenly spaced (0.93–2.5 mm), so the same count is a different length in different places.
4. The middle layer and middle point were off by one compared with the cyan formula.
5. There was no minimum solid stretch between windows (cyan uses `max(window_width + 2, …)`).
6. The shift sign was the opposite of cyan's, and some code was never used.

**Decisions:**
- Work on PIXEL only, and make it as close to the cyan logic as possible.
- Assume the mesh will be changed so that every row has the same number of points. That fix is outside these scripts.

**What the `PIXEL cyan` copy changes:**
- One window width for all layers, taken from the middle layer, so the shift only ever grows.
- The cyan shift sign (`- shift`), which reverses the lean of the diagonals.
- The cyan minimum spacing between windows, and the cyan middle-layer and middle-point formulas.
- Unused code removed; named constants `SOLID = 3` and `WINDOW = 2`; a header that matches the real inputs and outputs.
- A warning when rows have different point counts.

**Check:** with cyan-equivalent inputs on the cyan grid, the new `get_data()` reproduced the cyan output exactly on all 100 rows.

**Left for later:** measuring windows in mm instead of point counts, spacing the pattern by height for the fanned layers, a minimum run length for the extruder in mm, and what index 2 should mean (slow extrusion at 1 mm/s or extruder off).

---

## 2. `facade form (clean)` (`facade_form.gh`)

**Goal:** a lighter copy that's easier to read, with exactly the same output.

**Changes:**
- New small helpers: `shape()`, `units_per_piece()`, `normal()` (this one was written out twice before), `value()` for slider defaults, and `polyline()`.
- `run()` split into two marked steps.
- f-strings, corrected comments, and a shorter header.

**Check:** exactly the same points (0.0 mm difference) and the same `info` text in 5 slider combinations, and the same as the live component.

---

## 3. `facade fold` (creases along mesh Z)

**Reference:** the `Spiral` cylinder script. Within each fold the offset ramps up linearly (`0.5 * (i % resolution)`), then drops back.

**Decisions (from our questions and answers):**
- In the mesh frame, the wall runs mostly along Y, and each layer's path runs along Z (top to foot). Creases run **along mesh Z**, so each layer is pushed out by one amount along its whole path, and that amount changes from layer to layer.
- Folds are spaced **by layer number**.
- Shape: a **0–1 blend slider**. At 0 it's a sawtooth (linear, as in the reference); at 1 it's a smooth sine wave.
- A **flip** toggle reverses the sawtooth.
- Layers may step out in front of the layer below, but the path must never loop back on itself.
- The ease-in at each run end is `RAMP = 3 mm` (first 10 mm; you asked for the fold to reach closer to the ends).
- Point spacing is left as it is (no extra points added).

**Inputs:** `fold_count` (0–20), `fold_depth_mm` (0–10), `blend` (0–1), `flip`.

**How it works:**
- Each point is moved along the outward normal in the layer plane. "Outward" means away from the nearest inner point.
- The run ends don't move. `clean()` drops points that would turn back on the path or sit closer than `MIN_GAP`.
- The point count stays the same (9334 → 9334), so the PIXEL index logic can be used on top of it later.

---

## 4. `facade fold (across)` (creases across the layers)

- Same as `facade fold`, except the fold position comes from each point's share of its layer's path length (0 at the top, 1 at the foot). The folds land at the same share of the path in every layer, so the creases run along the wall's length.
- `fold_count` counts folds along each layer's path.
- The sawtooth's drop now happens inside a layer, between two neighbouring points. The jump there is about the fold depth.

---

## 5. `facade fold (wave)` and `facade fold (across, wave)`

**Goal:** fold lines that swing in a sine wave, controlled by sliders.

**Decisions:**
- `line_amp` (0–1): how far the lines swing, as a share of the fold spacing. 0 = straight lines.
- `line_waves`: a separate slider for the number of sine waves along each line.
- `line_phase` (0–1): how much each fold line's sine is shifted from the previous line's. 0 = all lines swing in step.

**Formula:** one helper places every point in the fold pattern. The fold lines sit at whole numbers:

```
pos = count * x - line_amp * sin(2π * (line_waves * y + line_phase * count * x))
```

- In the Z version, x = layer position and y = position along the path.
- In the across version, the two swap.

**Check:**
- With `line_amp = 0`, both give exactly the same output as the versions without the wave.
- With the wave on, every point's push matched the formula, the run ends didn't move, no path looped, and no points were dropped.

---

## Learnings

- **Test against a known answer.** We rebuilt cyan's inputs and compared outputs, compared the clean copy point by point with the original, and set `line_amp = 0` to compare with the earlier versions. These caught mistakes that "no errors on the canvas" would have missed.
- **A pattern built for an even grid needs even rows.** Counting points only works when the points are evenly spaced and every row has the same number. Most of the PIXEL problems came from that.
- **Anything that builds up over the layers must not depend on a value that changes per layer.** The old PIXEL shift used a width that changed each layer, so it jumped backwards.
- **"Along Z" needs a stated frame.** The wall is printed lying down, so the printing Z and the mesh Z are different directions. Name the frame before deciding fold directions.
- **Change one thing per version.** Each fold version changes one idea and leaves the others alone, so differences are easy to trace.

## Pitfalls

**Printing:**
- A sawtooth drop **across layers** (`facade fold`, `blend` = 0) is a full-depth step between two layers. With a 3 mm bead and 3 mm depth, the stepped-out bead has almost nothing under it. Check those layers in simulation, or raise `blend`.
- A sawtooth drop **within a layer** (the across versions) is a short robot move of about the fold depth. Check it in simulation too.
- Pushing the path out stretches the gaps between points beyond `PT_DIST` (2.5 mm). At the run ends, the 3 mm ramp gives gaps up to about 6.8 mm at a 10 mm depth. We decided to leave the spacing as it is.
- High `line_amp` together with high `line_phase` bends neighbouring fold lines into each other. The lines stay clean while `2π × line_amp × line_phase < 1`.
- PIXEL with `int_step` = 0.1 reaches the minimum window spacing in the upper layers (10 window points, 2 solid points).

**Grasshopper / Rhino 8 scripting:**
- `rg.Polyline(python_list)` picks the wrong .NET constructor (the integer one) and crashes. Build the polyline point by point (`polyline()` helper).
- `Plane.FitPlaneToPoints` returns a `(result, plane)` tuple in CPython (`fit_plane()` helper).
- .NET methods with `out` parameters return tuples in CPython: `_, t = crv.ClosestPoint(p)`.
- Script inputs without a type hint come in as plain values: sliders give numbers and toggles give booleans. Geometry inputs may come in as document ids, which is why `pt()` / `branches()` switch `sc.doc` to `ghdoc`.
- Copying a script component in code (`GH_Archive`) has to run on Rhino's UI thread. Copying through the Grasshopper clipboard returned nothing.
- Test scripts sent through the bridge share Python with Grasshopper. Running a heavy test while the canvas is solving gave wrong component output (missing points). Read a component's output only after its solve has finished, with nothing else running.
- A new component is solved after it's added to the canvas, so its output is empty if you read it straight away. Wait for the solve before checking.

## Not done yet

- Connect the chosen fold version into `merge layers` (the print chain).
- Combine a fold version with the PIXEL index pattern. The point count is kept for this.
- Change the mesh so every row has the same number of points, which PIXEL needs.
- The PIXEL questions left for later: windows in mm, what index 2 should mean, the minimum extruder run length, and the diagonal lean direction.
