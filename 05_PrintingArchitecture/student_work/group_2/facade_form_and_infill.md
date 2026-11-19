# Facade form and infill

A summary of the work in `facade_form.gh` (group_2): a lighter, cached Y blocks; one fold component; the facade form as a second design option; and linear infill (ribs and webs) from the facade face to the inner curve. It is written to be read at the start of a new conversation, so no other file is needed for context. Earlier work (the PIXEL pattern and the first fold versions) is in `facade_development.md`.

Words used here:
- **facade**: a railing wall (blocks 18–29 of Y blocks, `facade_component`). It is printed lying down: one layer = one cross section.
- **external**: the facade face (red label). **inner**: the inner curve facing the deck (blue). **other**: the foot, tongue, contact face and end faces (grey).
- **push**: how far a point of the external path is moved out from where `wall pts` put it.

## The final chain

```
Cluster -> Mesh -> Y blocks (lean, cached) .facade_component
        -> wall pts (cached) -> external / inner / other
        -> facade fold (all) .folded  OR  facade form (clean, live) .textured   (facade_option 0 / 1, Stream Filter)
        -> facade infill (v3) .infilled  (original = wall pts external, inner, other)
        -> merge layers (live) .external   (inner / other from wall pts (cached))
        -> PolyLine -> bead preview (live)
```

There are 45 enabled objects: these components, their sliders, the `infill` toggle, the Colour Swatch, and the Cluster with its 2 sliders. All other components are disabled and kept in the red "OLD COMPONENTS (HISTORY)" area on the left. The LAMCP component, its toggle and its panel are only the bridge to Claude.

| Component (group) | What it does | Inputs → outputs |
|---|---|---|
| `Y blocks (lean, cached)` [S1c] | Same output as the original `Y blocks`, about 250 lines shorter. The surface, blocks, walls and previews are cached. | The 16 Y blocks sliders (no `bridge_no`) → `layers`, `index`, `vectors` (print path of `print_block`), `blocks`, `facade_component` (the wall `facade_no`), `on_bed`, `centers`, `all_blocks`. The `info` text is printed: turn on the component's `out` output to see it. |
| `wall pts (cached)` [S2b] | Original `wall pts` slicing; slices again only when the wall mesh changes. The label under it says "sliced" or "reused". | `mesh` → `external`, `inner`, `other` ([layer][Point3d]) |
| `facade fold (all)` [S2a] | Replaces the four fold versions. | `external`, `inner`, `fold_count`, `fold_depth_mm`, `blend`, `flip`, `across`, `line_amp`, `line_waves`, `line_phase` → `folded`, `info` |
| `facade form (clean, live)` [S4] | Same code as `facade form (clean)`, fed from `wall pts (cached)`. Shares the form sliders with the original. | `external`, `inner`, `pitch_mm`, `bulge_mm`, `wave_count`, `wave_amp` → `textured`, `info` |
| `facade_option` + Stream Filter [S4] | Design option switch. | 0 = fold, 1 = form |
| `facade infill (v3)` [S3b] | Ribs at the creases of any pattern, plus optional webs. | `original`, `external`, `inner`, `other` (tree access), `infill`, `rib_count` → `infilled`, `ribs` (polylines), `info` |
| `merge layers (live)`, `PolyLine`, `bead preview (live)` [S2b] | Join the three groups into one closed loop per layer, with `index` and `vectors`, and preview it. | Same code as the original `merge layers` |

## How the infill works (`facade infill (v3)`)

- **Creases**: found from the push of every point, so the pattern code is not needed.
  - **Step**: a jump in push of `STEP` (1 mm) or more next to a low point. This is the sawtooth drop. The U starts on the top of the step; for a step up (flip), it ends on the top.
  - **V**: the push rises by at least `MIN_RISE` (0.3 mm) within `WINDOW` (6 mm) on both sides. This is the form's unit line. The U is centred on it.
  - **Along-Z fold**: there are no creases inside a layer. Use `rib_count`.
- **Rib (U)**:
  - Two legs, square to the facade face, in the layer plane, exactly one bead (`LINE_W` 3 mm) apart and parallel.
  - The far side ends where it is one bead from the inner path. This is found by bisection, checked at both corners and half way between.
  - The face points inside the tuck are replaced by the U. Neighbours closer than `MIN_GAP` (0.9 mm, straight distance) are dropped. The run ends never move.
- **Webs**: `rib_count` > 0 adds ribs at shares (i + 0.5) / rib_count of every run, the same in every layer, so they stack into webs.
- **Skip rules**:
  - **gap**: a leg would be shorter than one bead, which means the gap at the low side is under `MIN_RIB` (6 mm).
  - **other**: a foot, tongue or end-face point is nearer than the inner curve plus one bead. Without this rule the ribs ran diagonally through the solid foot.
  - **end**: too close to a run end.
  - **overlap**: too close to the previous rib.
- **Thin walls get no ribs; thick walls get them.** The infill switches on by itself as `facade_thickness_mm` grows. With 6 mm there are 0 ribs; with 16 mm there are about 500. A larger model scale alone does not thicken the wall.
- **Points**: at most `PT_DIST` (2.5 mm) apart on the ribs. The sharpest turn added was 98.7°, under the 104° MoveP limit (`MAX_TURN`).

## Stage history (what was made, tested and kept)

| Stage | Component | Status | Test |
|---|---|---|---|
| 1a | (read-only baseline) | – | 8 cases saved; profile showed where the time goes |
| 1b | `Y blocks (lean)` | superseded by 1c | 0.0 mm on all 8 outputs in 8 cases and on the canvas; canvas 48.4 s → 35.9 s (block 16) |
| 1c | `Y blocks (lean, cached)` | FINAL | 0.0 mm in all cases; build 9 s, then wall 2.2 s, side strip 6 s (was 12–20 s); rebuilds on a shape input or a moved mesh vertex |
| 2a | `facade fold (all)` | FINAL | 0.0 mm against the four versions live and in 24 extra settings |
| 2b | `wall pts (cached)` + live chain | FINAL | 0.0 mm against `wall pts`; reuse 0.47 s instead of 1.5 s |
| 3a | `facade fold (all, infill)` | superseded | first infill: U from the dip, toward the nearest inner point |
| 3a-B | `facade infill` | superseded by v2 | generic creases, U anchored on the step top; profile kept 98.8% (3a: 96.2%) |
| 4 | `facade form (clean, live)`, `facade_option`, `facade infill (v2)` | FINAL switch and form; v2 superseded by v3 | form copy 0.0 mm; v2 = v1 on the fold; on the form, clearance 3.0 mm and step ≥ 0.9 mm |
| 3b | `facade infill (v3)` + `rib_count` | FINAL | `rib_count` 0 = v2 exactly; webs stack (median shift 1.05 mm per layer); no turn over 104° added |

## Decisions

1. **Spiral contouring is out of scope.** Y blocks prints closed loops per layer. A component in `design_weijiun.gh` later joins them into one list of frames for the robot.
2. **Rewrites keep the output exactly.** Every copy was compared point by point (0.0 mm) before it was used. Exceptions, each listed when made:
   - the `k` bug fix: `info` now shows the right block number;
   - the obsolete double-wall lines removed from `info`.
3. **Never edit existing components.** Make a copy, test it, then rewire. Superseded versions stay, disabled, in the history area.
4. **Outputs**: keep the print outputs plus the previews that show which block is targeted. Dropped: `bridge_component` and `bridge_no`.
5. **Cache over merging.** The fold stays a separate component, so moving a fold slider never re-runs Y blocks. The caches are in Y blocks (blocks) and `wall pts` (slices).
6. **Facade = railing wall, facade face = its external (red) face.** The live chain uses the live wall (`facade_no` 3 = wall 21), not the mesh saved inside the original `wall pts`, which is an older wall 21 from a smaller model size.
7. **One fold component.** `across` picks the fold-line direction; `line_amp` = 0 gives the plain versions.
8. **Infill comes from the facade side; the inner curve stays clean.** It is a U with a parallel return one bead along that stops one bead short of the inner path. It is not a loop back to the same point.
9. **The tuck sits in the crease (option B).** It starts on the top of the sawtooth step, so the drop becomes part of the rib; on a V it is centred. A narrower U and a V-shaped rib were the alternatives, not taken.
10. **Infill switches on by the measured gap, not by the scale number.** The `infill` toggle forces it off.
11. **Infill is its own pattern-independent component**, so it serves the fold, the form and any later pattern.
12. **Webs for the along-Z fold** come from fixed shares of the path (`rib_count`).
13. **Saving the .gh is done by the user.** Canvas groups are tagged by stage [S1b]…[S4] with FINAL or superseded.

## Learnings

- **Measure before optimising.** The 12 wall preview meshes took about 7 s of every Y blocks solve, more than the slicing of a wall. Only the profile showed it.
- **An exact-output rewrite can still be faster.** Skipping `section()` results that were never used removed 29–55% of the surface projections with the same output.
- **Choose a number that measures the goal.** The first "option B" (U centred on the step) kept less of the fold (95.2%) than the version it replaced (96.2%). The sawtooth steps are only 1.1–2.5 mm wide along the wall, narrower than a bead. Anchoring on the step top gave 98.8%.
- **Fix the cause, not the symptom.** Sharp turns (up to 130°) came from a leg direction tilted by the inner curve and by a tangent taken across the step. Square legs and a one-sided tangent fixed them; corner chamfers were not needed.
- **Measure the gap where the rib is weakest:** at the low side of the crease, as a minimum leg length.
- **Along the path and straight across can differ.** Across a V, two points far apart along the path can be close in a straight line. Check minimum gaps as straight distances.
- **Check a pattern alone before blaming the infill.** The form's own 104.1° turn and the fold's 3.6 mm point gaps exist without any infill.
- **Change one thing per copy and test against a known answer**, same as in `facade_development.md`.

## Pitfalls

**Grasshopper / Rhino 8 scripting**
- **Cached objects and `isinstance()`**: a cache in `scriptcontext.sticky` holds objects from an earlier run of the script. After Grasshopper re-runs the script, its classes are new, so `isinstance()` fails. Use a flag such as `is_wall`.
- **New script inputs**: they get item access and the "ghdoc Object" hint. Set tree access for point trees. The fold and infill scripts convert ids themselves (`branches()` switches `sc.doc` to `ghdoc`).
- **Copying objects in code**: copied sliders and toggles need `CreateAttributes()` before they are placed.
- **Object identity**: comparing Rhino objects with `is` does not work (each access makes a new wrapper). Compare `InstanceGuid`.
- **`print()` output**: it only shows on the canvas when the script component's `out` output is turned on.
- **Disabled toggles**: a disabled toggle sends nothing, so the script sees `None`. The `infill` toggle off this way made the chain print without ribs, with no error.
- **Shared sliders**: one slider wired to several components re-runs all of them. With three Y blocks copies a solve took about 90 s; disable superseded copies.
- **Bridge (LAMCP)**: loading another .gh into a `GH_Document` from the bridge hung and then crashed Rhino. Polling the bridge during a solve slows the solve. A script runs about 1.3× slower as a canvas component than run in the bridge, so compare old and new code in the same setting.
- **`rg.Polyline(list)`**: picks the wrong constructor. Add points one by one.

**Printing**
- **Ribs and webs** are extra moves with the extruder on inside every layer. Check them in simulation before printing.
- **Web starts**: where the gap or foot rule switches between layers, a web starts over the empty cavity of the layer below (18 of 341 in the test) and bridges.
- **Point gaps**: the fold stretches some point gaps to 3.6 mm (more than `PT_DIST`). This is not caused by the infill.
- **The form**: one turn of 104.1° sits at the edge of the MoveP limit. A rib can touch the outer skin with about 0.2 mm overlap where the face curves.
- **Fixed slicing settings**: `wall pts` uses fixed `LAYER_H` 1.3, `LINE_W` 3 and `PT_DIST` 2.5 mm, not the Y blocks sliders.
- **Keystone layers**: keystones (for example block 16) report layer heights of 0.00–2.72 mm and a "thinnest layer < 40 %" warning. Check them before printing.

## Canvas notes (panels)

The groups carry panels that explain them, checked against the scripts at the end of this conversation.
- **Corrected, with the wording below:** the fold panel, the `wall pts (cached)` panel and the infill panel.
- **Accurate as written:** the `facade_option` switch, `merge layers (live)` and the form panel.
- **Not added yet:** a note for the [S1c] Y blocks group, for example "Builds all blocks once and keeps them. `print_block` only re-slices. Turn on `out` to read the info."

If a script changes, update its panel. What the panels must say:
- **Fold controls**:
  - `blend` sets the fold profile (0 sawtooth, 1 sine).
  - `line_amp` swings the fold lines sideways; 0 = straight lines. `line_waves` and `line_phase` only act when `line_amp` > 0.
  - `fold_count` = number of folds, `fold_depth_mm` = push.
  - `flip` reverses the sawtooth; it has no effect at `blend` 1.
  - Crease ribs only appear with `across` = True. For along Z, use `rib_count`.
- **`wall pts (cached)`**: it slices again when the wall mesh changes (`facade_no` or a shape slider). It reuses the slices when only `print_block` or a slicing input changes.
- **Infill**: U ribs from the creases to one bead short of the inner curve; only where the gap is at least 6 mm and the foot or tongue is not nearer; `rib_count` adds webs. Not yet checked in simulation.

## Future steps

1. **Inbuilt railing / seating on the non-facade face** (next conversation). The user confirmed that this is the inner curve facing the deck (`inner`, blue). Constraints from this work:
   - **Placement**: put the new component between `wall pts (cached).inner` and both `facade infill (v3).inner` and `merge layers (live).inner`, so the ribs stop one bead from the changed inner path. Do not change `other` (tongue, foot and contact face must still fit the shell).
   - **Effect on the ribs**: pushing the inner face into the cavity reduces the gap, so fewer ribs pass the 6 mm rule. Pushing it out toward the deck keeps them.
   - **Path rules**: keep run ends fixed, points 0.9–2.5 mm apart, turns ≤ 104°, layers planar. The inner run is joined to the others in `merge layers` by nearest run start.
   - **Load**: seating is a structural load on a printed wall, so check the bead count and wall thickness there, not only the shape.
2. **Simulation**: check the infill paths (web starts, sawtooth steps) and the keystone layers.
3. **Print settings in `wall pts`**: consider wiring them to the Y blocks sliders instead of the fixed constants.
4. **Saving**: save the .gh after each session. The code lives only inside the components, and the test copies made during this session were in a temporary folder.
