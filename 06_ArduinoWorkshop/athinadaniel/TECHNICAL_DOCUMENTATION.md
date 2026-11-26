# Interactive Chocolate Dispenser: technical documentation

MAS ETH DFAB · preliminary fabrication package · revision P1 (26.11.2026)

Units: millimetres. Origin: bottom centre of the lower module. X is width, Y is depth and Z is height. The front faces −Y.
Every dimension marked **(VERIFY)** is a reference value from datasheets or photographs, not a physical measurement. All of them are parameters in `source/chocolate_dispenser.py → P`. Change them there and regenerate.

---

## 1. Package contents

| File / folder | Content |
|---|---|
| `Chocolate_Dispenser_Assembly.3dm` | Rhino 7 file in mm. 136 named objects on layers 00–16. Mechanism states B and C are on hidden sublayers of `06_DISPENSING_MECHANISM`. It also holds swept envelopes, cable routes, dimension dots and the print-plate layout (layer 16). |
| `Chocolate_Dispenser_Exploded.3dm` | All components exploded along their assembly vectors |
| `Chocolate_Dispenser_Assembly.step` | **Exact B-rep NURBS solids**: named and coloured assembly. Use this in Rhino when you need editable closed polysurfaces. |
| `STEP_parts/*.step` | One exact solid per part, in assembly position |
| `STL_print_oriented/*.stl`, `3MF_print_oriented/*.3mf` | Printable parts, 1:1 in mm, already rotated into print orientation and placed on Z=0. All are watertight and manifold. |
| `Chocolate_Dispenser_Assembly.obj` + `.mtl` | Named mesh objects (`o P01_…`), grouped by layer. **OBJ has no unit field: import at scale 1.0 in millimetres.** |
| `source/` | `chocolate_dispenser.py` (all parameters and geometry), `validate.py`, `export_all.py`, `render.py`, `render_views.py` |
| `renders/` | Views generated from the CAD geometry (not imagined) |
| `validation_report.json`, `parts_table.json`, `print_plates.json` | Machine-readable check results, part data and plate grouping |

About the Rhino files: rhino3dm cannot write trimmed NURBS solids from OpenCascade. The 3dm files therefore contain high-resolution render meshes on the full layer structure, and the exact solids are in the STEP files. For editable solids in Rhino, `Import` the assembly STEP (names are kept) and move the objects onto the 3dm layers, or regenerate from the script.

Regenerate everything with `pip install cadquery rhino3dm trimesh numba`, then `python export_all.py OUT && python validate.py && python render_views.py OUT/renders`.

---

## 2. Concept and overall dimensions

The dispenser is a slim vertical tower in two printed shells that meet at an intentional seam at Z 80. That seam is also the functional split between the **mechanism zone** below and the **storage and interaction zone** above.

- **Left column:** a vertical chocolate magazine with a sight slot, so passers-by can see how many chocolates are left. The red refill lid sits on top.
- **Right column:** a graphite front-interface panel with the LCD, a NeoPixel "signal" light, the PIR lens and the IR rangefinder, all on one vertical axis.
- **Base:** the rotary-drum dispenser, the exit ramp and a full-width collection tray.

| | mm |
|---|---|
| Enclosure W × D × H | **150 × 82 × 250** (+4 lid) |
| Tray projection | 58 in front of the face, underside at Z −3 |
| Depth including cleat and bracket | 82 + 8 + 5 = 95 to the upright face |
| Lower module / upper column | Z 0–80 / Z 80–250 |
| Capacity | 11 chocolates (1 in the pocket + 10 in the tube), parameter `N_CAP` |
| Estimated filament | ≈ 500 g in total (3 perimeters, 15 % infill) |

I chose the depth (82) and width (150) for these reasons:
- The width has to hold the drum housing (47) and the LCD with its I2C connector (90).
- The depth has to hold the LCD stack (24), plus the 30 mm jumper-wire allowance above the breadboard, plus 9 mm free.
- The 250 mm height lets the upper column (176 tall printed upside down) and the rear cover (250) fit the A1's 256 mm build volume.

---

## 3. Dispensing mechanism

### 3.1 Principle: rotary drum with one single-chocolate pocket

- Chocolates lie flat in a 33 × 33 mm magazine tube, with 1.5 mm clearance around a 30 × 30 × 15 chocolate.
- Below the tube is a **Ø54 × 38 PETG drum**. Its axis is horizontal along X and coaxial with the servo.
- The drum has a **33 × 33 pocket exactly one chocolate deep (15 mm)**. A chocolate in the pocket sits flush with the top of the drum, so the next chocolate rests on top of it and **cannot enter the pocket**.

| Step | Drum angle (toward the front) | What happens |
|---|---|---|
| A rest | 0° | The pocket faces up and is filled by gravity from the stack |
| B transfer | 0° → 65° | The trailing corner of chocolate #1 lifts the stack by ≤ 3.9 mm. Corner-on-flat contact means the force on chocolate #2 is vertical, so nothing is sheared. Chocolate #1 then travels inside the R32 transport shell. |
| C dispense | 130° | The pocket mouth spans 92°–168°, entirely inside the release window (85°–168°). Gravity along the pocket axis (0.64 g) is more than wall friction (0.31 g at μ = 0.4), so the chocolate slides out onto the 30° ramp, drops about 22 mm, and lands in the tray. |
| Return | 130° → 0° | Chocolate #2 drops into the pocket as soon as the mouth arrives under the magazine |

Why I chose this over the alternatives in the brief:
- **Sliding gate or double gate:** a linear slider needs free travel equal to one pocket (about 38 mm) on the side away from the exit, which would put it inside the side wall of a slim tower.
- **Pivoting flap:** it cannot reliably retain the rest of the stack.
- **Horizontal rotary disc:** it needs a disc of about 110 mm diameter.
- **The drum:** it uses one servo with direct drive and no linkage, and it is self-sealing. When the drum turns, the solid part of the drum closes off the magazine.

### 3.2 Servo integration (DM996)

The drive train, in order: servo spline → **original cross horn**, keyed into a 1.6 mm deep pocket in **P12 horn adapter** and held with 2 × M2 screws → adapter fastened to the drum face with 3 × M3 screws into heat-set inserts.

- **Bearings:** the drum runs on a printed Ø10 axle stub in the left cheek of the housing. The adapter (Ø30) runs in a journal bore in **P11 servo bracket**. Radial load goes into the printed bearings, and the servo only supplies torque.
- **No printed spline:** the original horn is the only interface to the shaft.
- **Horn screw access:** a Ø4.4 axial bore through the axle, drum and adapter lets you tighten the horn screw after assembly, from the left side.
- **Mounting:** the servo slides through the bracket's mounting plate from +X. Its flanges sit on 4 M3 heat-set inserts.
- **Cable:** it exits at the far end of the servo body, away from every moving part.
- **Clearance:** the horn swing radius is 20 mm, and the nearest bracket rail is 22 mm from the axis.

**Estimated torque** (see `validation_report.json`):
- Stack load: 10 × 10 g = 0.98 N
- Lifting it with a 15 mm lever arm: 0.015 N·m
- Drum surface friction (μ 0.5, r 27): 0.013 N·m
- Total: about **0.03 N·m**, against roughly 0.9 N·m for the DM996. That is about 30× margin for normal operation.

The margin only covers normal operation. A jammed wrapper is not bounded by this estimate, so set software limits (§9).

### 3.3 Calibration of physical angles (VERIFY)

The commanded 0–180 range is **not** the physical rotation.
1. With the drum assembled but the horn not yet screwed on, use your `ESP32Servo` calibration sketch (750–2250 µs) to find the command that matches each physical angle.
2. Press the horn on so that the **pocket points straight up at the command you choose for `SERVO_REST`** (pick something around 20–30, not 0).
3. Increase the command until the pocket faces about 130° toward the front. That value is `SERVO_DISPENSE`.
4. Keep at least 10° away from both mechanical end stops.

---

## 4. Electronics integration

| Component | Location / mounting |
|---|---|
| Breadboard 160 × 55 + Nano ESP32 | Vertical on **P05 tray**. The tray slides into T-slot rails on the inside of the rear cover (bottom stop, side locators, 2 snap clips). Space in front of it: 30 mm wiring allowance + 9 mm free. **Removing the rear cover brings the whole breadboard out for debugging.** |
| LCD 1602 + I2C backpack | Panel window 65.5 × 17 with a 45° outward chamfer. 4 posts, 7 mm tall (bezel height), with M2.5 self-tapping screws. The PCB and backpack are hidden. 10 mm is reserved on the right for the I2C connector (envelope on layer 13). |
| NeoPixel | Slides into a slot at the back of a 12 mm light chamber. Its walls stop light leaking into the enclosure, and the distance cuts hotspots. **P15 diffuser** (Ø16 visible) is removable from inside. |
| PIR HC-SR501 | Ø23.8 opening with an outer chamfer. The lens protrudes about 6 mm for a wide field of view. PCB on 2 posts, M2. |
| Sharp IR | Open window (no cover, no recess) with a 45° flare in front of both optics. M3 into inserts through the sensor ears. |
| Servo power | External DC enters through a Ø9 hole in the rear cover at the bottom right, through **P18 strain relief**, then up the rear-right channel to the breadboard power rail. **Common GND with the Nano.** |
| USB-C | Leaves through a 16 × 10 opening in the rear cover in line with the Nano. **Use a right-angle USB-C cable**, because there is only about 3.6 mm above the breadboard. |
| Separation | P06 electronics floor at Z 80–82.4 separates the wiring from the servo and drum. The column partition separates the chocolates from the electronics. The servo cable passes through a filleted slot. |

Pins are unchanged: D3 NeoPixel, D5 PIR, D6 servo, A0 IR, A4/A5 I2C.

**Power:** a 1 A supply is marginal. The DM996 stall current is about 2.5 A, and start-up peaks can brown out the supply. Use **5–6 V at ≥ 2 A** with a 470–1000 µF capacitor across the servo rail. The Hama adapter at 6 V is fine for bench tests. There is no mains voltage inside the enclosure.

---

## 5. Bill of materials

### 5.1 Printed parts (`parts_table.json` has the full data)

| # | Part | Material | Print bbox (mm) | ≈ g | Orientation / supports |
|---|---|---|---|---|---|
| P01 | Lower module (mechanism housing, outlet) | PLA matte white | 150×79×80 | 67 | Upright, floor on bed. Outlet top edge = 36 mm bridge. |
| P02 | Upper column (storage + electronics) | PLA matte white | 150×79×176 | 102 | **Upside down**, roof on bed. No supports. |
| P03 | Front interface panel | PLA matte graphite | 94×167×23 | 34 | **Face down**, clean front. Posts point up. |
| P04 | Rear maintenance cover + cleat + tray rails | **PETG** | 150×250×16 | 81 | Outer face on bed. Cleat at 45°. |
| P05 | Electronics tray | PLA | 68×164×13 | 15 | Flat |
| P06 | Electronics floor / partition | PLA | 91×74×2.4 | 11 | Flat |
| P07 | Chocolate magazine (flanged tube) | PETG (translucent optional) | 45×45×167 | 38 | Upright |
| P08 | Refill lid | PLA signal red | 45×45×9 | 5 | Top face down |
| P09 | Dispenser housing | PETG | 85×66×48 | 31 | On the left cheek (bore vertical). No supports. |
| P10 | Rotary drum | PETG | 54×54×43 | 22 | Axis vertical, pocket opening sideways. 3 mm fillets. |
| P11 | Servo bracket + bearing plate | PETG | 73×66×22 | 22 | On the bearing plate |
| P12 | Horn adapter | PETG | 30×30×11 | 3 | Horn pocket up |
| P13 | Exit chute / ramp | PETG | 28×31×38 | 7 | On its side (extruded profile) |
| P14 | Collection tray | PLA matte graphite | 150×93×20 | 34 | Upright. The underside pocket bridges 18 mm, so enable "bridge" settings. |
| P15 | NeoPixel diffuser | PETG natural / translucent white | 20×20×6 | 1 | Face down |
| P16 | Shelving mount bracket | PETG, 4 walls | 54×150×19 | 22 | Plate on bed. Hooks at 45°. |
| P17 | Cable comb | PLA | 10×8×12 | 1 | — |
| P18 | Strain relief | PETG | 18×10×16 | 1 | — |
| P19 | Outlet flap (optional finger guard) | TPU 95A | 34×19×0.8 | 1 | Flat |
| P20 | Tolerance coupon (print first) | Production material | 60×20×10 | 3 | Flat |

### 5.2 Parallel printing plan (A1, 0.4 nozzle, 0.2 layers)

The times below are rough estimates, about 12–15 g/h. Bambu Studio will give the real numbers. With 4 printers the whole set prints in about one long session.

| Printer | Plate | Est. time |
|---|---|---|
| 1 | P02 upper column (PLA white) | ≈ 7–8 h |
| 2 | P01 lower module + P05 + P06 + P17 + P20 (PLA white) | ≈ 6–7 h |
| 3 | P04 rear cover + P16 bracket + P12 adapter (PETG) | ≈ 7 h |
| 4 | P09 + P10 + P11 + P07 + P13 + P18 (PETG), then P03 + P14 (PLA graphite), then P08 (red), P15, P19 | ≈ 6 h + 5 h + short jobs |

Layer 16 of the 3dm shows a packed layout per material (`print_plates.json`).

### 5.3 Hardware

| Qty | Item | Use |
|---|---|---|
| ≈ 30 | M3 brass heat-set inserts, Ø4.0 × 5 (VERIFY with P20) | Bosses, posts, frame, bracket, drum |
| 8 | M3 × 10 countersunk | Rear cover |
| 4 | M3 × 10 | Bracket → housing frame |
| 4 | M3 × 8 + washers | Servo flanges (the flange holes are Ø4.4) |
| 4 | M3 × 10 | Mechanism feet → floor |
| 4 | M3 × 8 | Electronics floor → posts |
| 2 | M3 × 8 countersunk | Tray → floor (from below) |
| 2 | M3 × 8 | Front panel tab → roof bosses |
| 3 | M3 × 10 | Adapter → drum |
| 2 | M3 × 6 | IR sensor |
| 1 | M3 × 10 | Cable comb |
| 2 | M2 × 8 self-tapping | Horn → adapter |
| 2 | M2 × 5 self-tapping | PIR PCB |
| 4 | M2.5 × 6 self-tapping | LCD |
| 2 | M4 × 16 + washer + wing nut | Bracket → upright |
| — | Right-angle USB-C cable, 2 A 5–6 V DC supply, 1000 µF capacitor, dupont jumpers (right-angle headers recommended on the LCD backpack) | — |

---

## 6. Assembly sequence

There are no trapped or inaccessible screws.

1. Print **P20** and check the insert and clearance holes. Adjust `M3_INSERT`, `CLR` and `CLR_ROT` if needed and regenerate.
2. Press in all heat-set inserts (P01 floor bosses and posts, P01/P02 rear bosses, P09 frame, P11 servo plate, P10 drum face, P02 roof bosses, P03 IR posts).
3. **Mechanism module (on the bench):**
   1. Put the drum's axle stub into the left cheek of P09 and slide the drum in from the right.
   2. Screw P12 to the drum (3 × M3).
   3. Bolt P11 to the P09 frame (4 × M3). The adapter now runs in the bracket journal.
   4. Set the servo to `SERVO_REST`, push it in from +X through the mounting plate and screw the flanges (4 × M3).
   5. Press the horn into the adapter's key pocket with the drum pocket pointing up. Fix it with 2 × M2.
   6. Tighten the horn screw through the axial bore from the left.
   7. Check that the drum turns freely through 0–130°.
4. Put **P13 chute** into P01, with its lip through the outlet. Optionally hang **P19 flap** behind the outlet.
5. Lower the mechanism module into P01, between the chute and the right wall. Screw it to the floor bosses (2 × M3 through the housing pads, 2 × M3 through the bracket foot).
6. Feed the servo cable up. Screw **P06 electronics floor** onto the 4 posts.
7. Mount the PIR, IR, LCD and NeoPixel on **P03**. Insert **P15**. Pre-wire long jumpers.
8. Place **P02** on P01. The right and front skirts locate it, and the column partition sits on P06.
9. Insert **P03** from inside: hook its bottom tongue behind the lower front wall, press the flange against the frame, and fix the top tab with 2 × M3 into the roof bosses.
10. Slide **P05**, with the breadboard and Nano, into the rails on **P04**. Connect everything and fit **P17** and **P18**.
11. Close **P04** (8 × M3 countersunk). It ties the two shells together.
12. Drop **P07** in from the top so it sits in the housing socket. Its flange sits flush in the roof recess. Fill it and fit **P08**.
13. Screw **P14** tray from below (2 × M3).
14. Install: hook **P16** into the upright perforations, add the 2 × M4 wing nuts, then hang the dispenser on the cleat.

**Refill:** lift P08 and drop chocolates in flat, **wrapper seam down, without twisted ends**. Keep 2 mm headroom below the lid. Nothing else needs opening.

**Maintenance:**
- **Electronics:** lift the unit off the cleat and remove P04. The breadboard tray slides out.
- **Mechanism (cleaning a jam):**
  1. Remove the magazine from the top, then P04.
  2. Unscrew the 4 feet screws and P06.
  3. Lift P02, then lift out the mechanism module.
  4. To reach the drum, remove the 4 bracket screws.
- Clean with a dry brush or isopropyl alcohol.

---

## 7. Validation: what was actually checked in CAD

| Check | Result |
|---|---|
| All 33 solids are valid OCC B-reps, closed shells, one solid per part | ✅ |
| All 20 printable STL exports are watertight and manifold | ✅ (the PIR reference dome mesh is not, but it is reference only) |
| Pairwise static interference across every part and component (> 0.5 mm³ threshold) | ✅ **0 conflicts** (component envelopes that intentionally contain their own parts are excluded) |
| Drum, adapter, horn and chocolate swept 0 → 130° in 10° steps against the housing, bracket, chute, lower module, magazine, servo, electronics floor and upper column | ✅ **0 collisions** |
| Chocolate corner radius 30.9 < transport shell R32 | ✅ |
| Pocket mouth at 130° (92–168°) inside the release window (85–168°) | ✅ |
| Pocket depth = 1 × chocolate thickness (< 1.5 ×) → one per cycle | ✅ |
| Magazine, pocket, outlet and tray share the axis X = −48.6 | ✅ |
| Ramp top below the drum shell (1.5 mm gap, smaller than a chocolate) | ✅ |
| Breadboard fits the electronics column (+3.6 mm), 8.9 mm free between the LCD stack and the wire envelope | ✅ |
| Servo flange top (Z 72.8) below the electronics floor (Z 80) | ✅ |
| Every printable part fits 256³ in its print orientation | ✅ |

**Not validated** (needs a physical prototype): dispensing reliability with real wrappers, real friction coefficients, actual torque and current, cleat and bracket load capacity, insert pull-out, sensor fields of view in the corridor, and food safety. FDM surfaces are not food-contact certified. **Use individually wrapped chocolates only.**

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Chocolate thickness or shape differs from 30×30×15, so the pocket holds 0 or 2 | Measure 10 pieces and set `CH_T`, `CH_W`, `CH_D`. Pocket depth = `CH_T` + `POCKET_TOP_OFFSET` (keep it within ±0.5). Regenerate P10, P09 and P07. |
| Twisted-end wrappers catch on the pocket edge | Use flat-wrapped pieces (square chocolates such as small Ritter or Lindt Napolitains). The 3 mm pocket fillets help. |
| **Finger access:** the pocket mouth is about 30 mm from the outlet | Fit the TPU flap P19. Move the servo slowly (2°/15 ms) and only after the 2 s presence check. Detach the servo after the return so it holds no torque. ISO 13857 distances for children are not met, so supervise use. |
| Stack lift (3.9 mm) jams in a full magazine | Torque margin is about 30×. If it occurs, reduce `N_CAP` or increase `DRUM_R` (lift = √(15² + R²) − R). |
| Servo brown-out on 1 A supply | ≥ 2 A supply + bulk capacitor (§4) |
| USB-C plug height above the breadboard | Right-angle USB-C, or move the Nano 25 mm down on the breadboard |
| LCD I2C connector width | 10 mm reserved. Bend the dupont leads or use right-angle headers. |
| Upright profile, hole pitch and size are unknown | **Measure** `UP_*`. P16 is a separate part and regenerates in minutes. |
| Door swing and circulation | From the photos, the door is hinged on the far jamb and swings away from the upright. The tray projects 153 mm from the upright face at about 1.05 m height. Confirm the clear corridor width on site. |
| Long thin print (P02) warps | Brim 5 mm, matte PLA, enclosure doors closed |

---

## 9. Servo movement sequence (for the existing sketch)

```cpp
// add: #include <ESP32Servo.h>   Servo drum;  attach in setup(): drum.setPeriodHertz(50); drum.attach(D6, 750, 2250);
const int SERVO_REST = 25, SERVO_DISPENSE = 155;   // command values from calibration (VERIFY)
enum State { IDLE, ARMED, DISPENSING, RETURNING, COOLDOWN };
// IDLE      : motionDetected (PIR && 10-60 cm) -> NeoPixel red, LCD "Wait for your chocolate!", t0 = millis(), ARMED
// ARMED     : if !motionDetected -> IDLE ; if millis()-t0 >= 2000 -> DISPENSING
// DISPENSING: step REST->DISPENSE by 2 deg every 15 ms (non-blocking), hold 400 ms -> RETURNING
// RETURNING : step back to REST, hold 300 ms, drum.detach() -> COOLDOWN (motionCount++ , MQTT publish "dispensed")
// COOLDOWN  : 4 s lockout, then IDLE (re-attach before next move)
```
Keep the existing non-blocking `millis()` structure. Never call `delay()` during a move while MQTT is active.

---

## 10. Unverified dimensions and assumptions (measure before final print)

1. Chocolate: 30 × 30 × 15 mm, about 10 g, flat wrapper.
2. DM996:
   - body 40.7 × 19.7 × 37 (case), 42.9 total with the spline
   - flange 54 long, 2.5 thick, 26.5 mm from the bottom
   - holes 48 × 10 mm, Ø4.4
   - shaft offset 10.15 mm
   - horn: cross shape, 20 mm radius, 6 mm arms, 2.5 thick; M2 holes at 15 mm radius
   - torque about 0.9 N·m
3. Breadboard 160 × 55 × 9. Nano on the breadboard about 13 mm tall. Jumper allowance 30 mm.
4. LCD:
   - PCB 80 × 36
   - bezel 71.2 × 24.2 × 7
   - view area 64.5 × 16, assumed centred on the PCB
   - holes 75 × 31
   - backpack 42 × 19 × 15
   - connector sideways, ≤ 10 mm
5. PIR: PCB 32 × 24, lens Ø23 × 12.5, holes 28 mm apart. IR: 44.5 × 18.9 × 13.5, ears 37 mm apart, optics 20 mm apart.
6. Heat-set insert hole Ø4.0. Clearances 0.4, rotating parts 0.6.
7. Shelving upright: 40 × 40 × 2 angle, slots 6 × 11 at 25 mm pitch, ±10 mm rows. **These are assumptions from photos; measure them.**
8. Installation height: unit bottom at 1050 mm above the finished floor (LCD at about 1258 mm).
