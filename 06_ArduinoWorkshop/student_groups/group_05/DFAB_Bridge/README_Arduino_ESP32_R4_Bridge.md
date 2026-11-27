# Arduino Nano ESP32 ↔ Nano R4 — Wi-Fi bridge, learnings & next steps

_Last updated: 2026-11-27 (Stages 0–6 ✅ on hardware; Stage 7 Wi-Fi + **HACK button** code done and simulated, hardware test pending; Stage 8 left). **Start with §0.** §8 holds the detailed decision log and supersedes conflicting lines in §1–7. Status labels: ✅ confirmed by user on hardware · ⚠️ unverified / open · ❌ known not working._

> Note: earlier sessions (cloud) could not compile. **Since Stage 0, Claude compile-checks locally** with the arduino-cli bundled in Arduino IDE 2 (Windows: `%LOCALAPPDATA%\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe`; FQBNs `arduino:esp32:nano_nora`, `arduino:renesas_uno:nanor4`). Compiling ≠ tested on hardware: the user still tests every stage.

---

## 0. Resume here (state 2026-11-27)

**Where we are:** Stages 0–6 are done and confirmed on hardware. **Stage 7 (ESP32's own Wi-Fi + pop-up page) and the
HACK button (7 regular songs on the knob + 7 HACK songs) are written, compiled (2 599 977 B, 82 %) and simulated, but not yet
tested on hardware** — the user put the hardware test on hold ("outstanding"). Then Stage 8 (integration) is the last stage.

### Outstanding — Stage 7 + HACK hardware test
Upload `esp32_wifi_to_r4` (double-tap the ESP32 reset button if the upload fails with `LIBUSB_ERROR_TIMEOUT`; compiling
takes ~1–2 min because of `sounds.h`). The R4 sketch is unchanged. Then:
1. Power up **without any hotspot** → within ~3 s a regular song plays, R4 LED green, motor follows the sliders, ESP32 yellow LED on.
2. Knob: 7 regular songs (Harlem Shake … Blue), each loops without a gap.
3. Android phone: join Wi-Fi **`DFAB-ESP32`** (open) → "Sign in to network" pop-up → page with the red **HACK** button.
   Fallback: `http://192.168.4.1`; if that fails too, mobile data off.
4. Press HACK → next HACK song plays once (page shows "HACK: <name>"), then the regular song restarts from its beginning.
5. Press again within 2 s → "Wait a moment…"; press during a HACK song → queued ("+1 waiting"). 8th press wraps to the first HACK song.
6. Second phone / iPhone / Mac / Windows laptop: pop-up or `http://192.168.4.1`, button works from all.
7. Range check from where visitors will stand. Heat check (R3, MOSFET) after ~10 min — `LOUDNESS = 0.8` means more continuous drive.

### HACK button — built 2026-11-27 (code + simulation, not on hardware)
- **Knob = 7 regular songs** (`role = channel`), **HACK list = 7 songs** (`role = hack`), both from `sounds/clips.csv`,
  all normal sampling (`LOUDNESS = 0.8`). Square-wave tone versions **dropped** (user). Tone player and the text box removed;
  `melodies.h` stays in the folder but is no longer included.
- Page: big round red **HACK** button (form POST `/hack` → redirect, so reloading never presses again) + "HACK: <name>" /
  "Playing: <name>", updated every 2 s via `/status` (small script; without JS it updates on the next press).
- Each accepted press = next HACK song, wraps after the last. Lock `HACK_LOCK_MS = 2000` (presses inside it → "Wait a moment…"),
  queue `MAX_QUEUED_HACKS = 10` ("Too many hacks waiting."). After the last queued HACK song the regular song restarts from
  its beginning; a knob change during a HACK song takes effect afterwards. Speed + drift apply to HACK songs too.
- **No visitor text reaches the R4 any more** (R4 only gets `S/W` lines). Any UDP packet to 192.168.4.1:4210 = one press (laptop tests).
- PWM stays in clip mode (40 kHz, 8 bit) all the time → the tone/clip mode-switch pop is gone.
- Simulation (`sim_hack.py`, scratchpad, real clip lengths): seamless loop 60 s (0 ticks silent); press → HACK song → regular
  restart after 16.95 s; lock rejects 0.5 s, accepts 2.5 s; page "HACK: Never Gonna Give You Up (+1 waiting)"; 9 presses →
  7 songs then wrap; queue never above 10; knob change applied after the HACK song; speed top → 17 s song lasts 11.33 s.

### Progress 2026-11-27 (HACK change, preparation)
- `sounds/` now has `Regular Songs/` and `Hack Songs/` — **the folders define the grouping** (user). Knob: Harlem Shake,
  Gangnam Style, All Star, Gut Genug (real song, 0:14–0:30), Macarena (0:41–0:59), Astronomia (0:18–0:33), Blue (0:31–0:45).
  HACK (play order): Never Gonna Give You Up, Buttercup, Curb Your Enthusiasm, Baby Shark, Axel F (0:33–0:48),
  My Heart Will Go On (0:19–0:38), What Does the Fox Say (0:40–0:55).
- `clips.csv` now `file,name,role,start,length_s` (file = path inside `sounds/`, role = `channel`/`hack`, row order = order).
  Converter writes `SOUND_CLIPS` + `SOUND_CLIP_COUNT` (knob, unchanged names → current sketch still compiles) and
  `HACK_CLIPS` + `HACK_CLIP_COUNT`. Previews named `channel_…` / `hack_…`. 14 clips = 1.80 MB (86 % of budget).
- Square-wave **tone versions** tested (`python/preview/hack_tone_test/*_TONES.wav`, librosa pyin melody → square notes):
  pitch confidence My Heart Will Go On 0.69, Gut Genug 0.48, Axel F 0.39, All Star 0.29, all others ≤ 0.18 → mostly
  unreliable → **user decided: no tone versions, normal sampling for all.**
- ⚠️ `LOUDNESS` in the converter was changed to **0.8** outside the session (was 0.45) → ~17–24 % of samples limited,
  similar to the square test. **User confirmed: keep 0.8** (louder, accepted compression). `sounds.h` generated with 0.8.
- Done: HACK button built (see section above). Outstanding: hardware test.

### Stage 8 (integration) — still to do
Full run on the power bank (≥ 15 min; bank auto-off/trickle mode §4.6), grounds per §7.7, both 12 V supplies + emergency
stop within reach, final clean-up of this README.

### Open items (not blocking)
- **Volume** is still soft. Done: loudness matching, now `LOUDNESS = 0.8` (user's choice 2026-11-27, heavily limited/louder).
  Hardware options (§8.4 table): speaker in a box/baffle;
  R3 100 Ω → 2 or 4 × 100 Ω in parallel (+5.7 / +11 dB) **plus a flyback diode** (1N5819/1N4001, stripe to +12 V);
  best: PAM8403 class-D amp module.
- Possible small pop when a clip *starts* (knob change / HACK) → 20 ms duty fade-in if it bothers.
- Mac: check Boards Manager shows **Arduino ESP32 Boards 2.0.18-arduino.5**; install **AccelStepper**; create the Python
  venv (`uv venv .venv --python 3.13`, then `.venv/bin/pip install numpy scipy soundfile librosa`).
- `python/send_command.py` is empty. Not needed: any UDP packet to 192.168.4.1:4210 counts as one HACK press.
- `python/preview/square_test/` and `python/preview/hack_tone_test/` hold rejected test previews (square-wave ideas) — safe to delete.
- Flash: sketch with 14 songs = 2 599 977 B (82 %); sound budget 2.1 MB, 1.80 MB used → room for ~35 s more audio at 8 kHz.
- Tempo middle is ×1.0026 (√(0.67·1.5)); `TEMPO_MIN = 0.6667` would make it exactly ×1.00.

### How to work on it
- Compile check (Windows): `%LOCALAPPDATA%\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe` with FQBNs `arduino:esp32:nano_nora` and `arduino:renesas_uno:nanor4`
  (AccelStepper: library must be installed, or pass `--libraries`).
- Songs: put the file in `sounds/Regular Songs/` (knob) or `sounds/Hack Songs/` (HACK button) and add a row to
  `sounds/clips.csv` (`file` = path inside `sounds/`, `name`, `role` = `channel`/`hack`, `start` mm:ss, `length_s`);
  row order = knob order / HACK play order. The converter refuses (and writes nothing) if the total doesn't fit.
- Sounds: edit `sounds/clips.csv` or settings in `python/convert_sounds.py` → run `.venv\Scripts\python python\convert_sounds.py` from `DFAB_Bridge`
  (macOS: `.venv/bin/python python/convert_sounds.py`) → listen to `python/preview/*.wav` → re-upload the ESP32.
- Settings in a sketch (tempo, detune, speeds, Wi-Fi) → re-upload only that board, no converter run.

### Wiring (current, all confirmed by the user)
| From | To | Notes |
|---|---|---|
| ESP32 D8 (TX) | R4 D0 (RX) | UART 9600, one-way. ESP32 D9 = RX, unused. |
| ESP32 GND | R4 GND | Always — needed on battery. |
| ESP32 D3 | R1 100 Ω → MOSFET 20N06L gate | R2 10 kΩ gate→source. Source → GND (ESP32 GND). |
| 12 V (speaker supply) + | speaker → R3 **100 Ω (2–5 W)** → MOSFET drain | No capacitor, **no flyback diode yet**. Supply − → GND. |
| ESP32 3V3 / GND | pots' outer pins | **Never VBUS/5 V** (was wrong once, fixed). |
| ESP32 A0 / A1 / A2 | knob (song) / speed slide / detune slide | 0–4095. |
| R4 D7 / D5 / D3 | driver PUL+ / DIR+ / ENA+ | PUL−, DIR−, ENA− → R4 GND. ENA HIGH = driver off (verified). |
| Driver | 17HS4401, own 12 V supply | DIP SW1–6 = **OFF ON OFF ON ON OFF** (1/8 = 1600 steps/rev, 1.5 A). |
| Power bank | USB-C of each board | Not VIN. Bank never powers the driver or the speaker. |

### Current settings (where to change them)
| What | Value | File / constant |
|---|---|---|
| Wi-Fi | own network `DFAB-ESP32`, open, channel 6, max 8 clients, page `http://192.168.4.1` | ESP32 `AP_SSID`, `AP_PASSWORD` (≥ 8 chars = WPA2), `AP_CHANNEL`, `AP_MAX_CLIENTS` |
| Knob | 7 regular songs (`role = channel`, row order of `clips.csv`) | `sounds/clips.csv` |
| HACK button | next of 7 HACK songs (`role = hack`, row order), wraps; 2 s lock; queue ≤ 10 | `sounds/clips.csv`, ESP32 `HACK_LOCK_MS`, `MAX_QUEUED_HACKS` |
| Tempo (speed slider) | ×0.67 … ×1.5, exponential; clips = varispeed (pitch follows) | ESP32 `TEMPO_MIN`, `TEMPO_MAX` |
| Detune (detune slider) | 0 … ±200 cents slow random drift (500 ms glides) | ESP32 `DETUNE_MAX_CENTS`, `WARBLE_MS` |
| Looping | regular songs loop seamlessly; HACK songs play once | ESP32 `REPEAT_PAUSE_MS = 0` |
| Pots | 8-sample average, smoothing 4, deadband 20 | ESP32 `POT_SAMPLES`, `POT_SMOOTHING`, `POT_DEADBAND` |
| Motor speed | 0 … 4800 steps/s (3 rev/s), stops below slider 100 | R4 `SPEED_MAX_STEPS_S`, `SPEED_STOP_THRESHOLD` |
| Ramp | 4800 steps/s² (1 s to full speed) | R4 `RAMP_STEPS_S2` |
| Dwell before reversing | 0.5 … 10 s (detune slider) | R4 `DWELL_MIN_MS`, `DWELL_MAX_MS` |
| Driver off when idle / link lost | 3 s / 2 s | R4 `IDLE_DISABLE_MS`, `FAILSAFE_TIMEOUT_MS` |
| Sound conversion | 8 kHz 8-bit, varispeed (1 variant), `LOUDNESS = 0.8` (user, 2026-11-27), high-pass 150 Hz | `python/convert_sounds.py` |

---

## 1. Hardware inventory

| Item | Notes |
|---|---|
| Arduino **Nano ESP32** (u-blox NORA-W106, ESP32-S3) | **3.3 V logic, pins NOT 5 V tolerant.** Wi-Fi + BLE. No DAC. VIN 6–21 V (cheat sheet also says 5–18 V; stay 6–18 V). |
| Arduino **Nano R4** (Renesas RA4M1) | **5 V logic** on all header pins. Input HIGH threshold ≈ 3.5–4 V. No Wi-Fi. Has RGB LED; the orange LED_BUILTIN is reported non-functional on some Nano R4 boards (user now uses RGB `LEDR/LEDG/LEDB`, active LOW). |
| Slide pot (HW-233) | Two outputs OTA / OTB (probably two tracks on one slider — verify with multimeter). |
| Rotary pot on breakout | 3-pin (GND / VCC / signal). |
| Stepper **17HS4401** (NEMA 17) | 1.8°/step (200 full steps/rev), 1.7 A/phase, ~1.5 Ω/phase. Identify coil pairs with a multimeter (~1.5 Ω within a pair, open between pairs); don't trust wire colours. |
| Microstep driver (TB6600-style, "Microstep Driver", 9–42 VDC) | Powered by separate **12 V** supply. Opto-isolated PUL/DIR/ENA inputs. |
| Speaker 4 Ω / 5 W | External 24 V supply available — **see hazard in §5**. |
| Breadboard, jumpers, resistors, **20N06L** logic-level N-MOSFET (TO-220) | Switches the speaker from **ESP32 D3** (originally drawn as D6) — see §5 and §0 wiring. |
| **Anker 533 Power Bank (PowerCore 30 W, A1256)** | 10,000 mAh / 36 Wh, 2× USB-C + 1× USB-A, 5 V⎓4.8 A total. Rated 5,700 mAh at 5 V. Has trickle mode (double-press button, ~2 h). |
| Also seen on the desk (not yet in scope) | HC-SR04 ultrasonic sensor (5 V echo — needs a divider for the ESP32), MAXPRO continuous-rotation servo. |

---

## 2. Current architecture (decisions)

```
Phones / laptop ──Wi-Fi "DFAB-ESP32"──► Nano ESP32 ──UART 9600, one-way──► Nano R4 ──► TB6600 ──► stepper
  pop-up page http://192.168.4.1          │  D8 (TX) ────────────────► D0 (RX)        D7/D5/D3
  red HACK button (UDP :4210 = 1 press)   │  GND ────────────────────► GND
                    knob A0, sliders A1/A2 ┘  D3 ──► MOSFET ──► speaker (12 V)
```
(State after Stage 7 + HACK button. Earlier versions used the phone hotspot and text messages — see rows below and §8.)

| Decision | Choice | Why |
|---|---|---|
| Role split | ESP32 = Wi-Fi + HACK page + pots + sound (7 knob songs, 7 HACK songs); R4 = stepper | ESP32 has Wi-Fi; R4's 5 V signals drive the TB6600 opto inputs reliably (3.3 V is borderline). |
| Board link | UART, **one-way ESP32 → R4**, 9600 baud, plain-text lines ending in `\n` | Simplest. Return path not wired yet. |
| ESP32 UART | `Serial1.begin(9600, SERIAL_8N1, D9, D8);` → TX on **D8** (GPIO17), RX on D9 (GPIO18) | See pitfalls §4.1. |
| R4 UART | `Serial1.begin(9600);` → RX on **D0**, TX on D1 | `Serial` on the R4 is USB. |
| Power | Power bank → **USB-C port of each board** (not VIN) | Bank only gives 5 V to a non-PD device; VIN needs ≥ 6 V. ✅ works. |
| Network (Stages 0–6, superseded) | Switched from ESP32 access point to **phone hotspot (station mode)** | Phone couldn't open the ESP32's own AP page; hotspot keeps laptop internet. AP version kept as fallback. |
| Network (Stage 7, final) | **Back to the ESP32's own access point**, open, with captive portal (DNS → 192.168.4.1) | User: visitors should send messages; hotspot would need sharing its password + changing IP. Captive portal's mini-browser is bound to the Wi-Fi, avoiding the old "phone routes via mobile data" problem. |
| Phone/laptop → ESP32 | Page on the ESP32's own network (`http://192.168.4.1`, pop-up) with the red **HACK** button; UDP packet to 192.168.4.1:4210 = one press | Each accepted press plays the next HACK song (2 s lock, queue ≤ 10). Since the HACK change **no visitor text reaches the R4** (it only receives `S/W` slider lines). |

---

## 3. Status log

| Item | Status |
|---|---|
| Powering both boards from the Anker bank via USB-C, GND ↔ GND between boards | ✅ |
| Stage 0 — `secrets.h`, sketch folders, `.gitignore` | ✅ (`secrets.h` unused since Stage 7) |
| Stage 1 — pots on ESP32 A0/A1/A2 (after moving pot VCC from VBUS to 3V3) | ✅ |
| Stage 2 — slider values ESP32 → R4 (`S#### W####`), 2 s failsafe | ✅ |
| Stage 3 — stepper: speed, dwell reversal with ramps, ENA idle-off, failsafe; later 4800 steps/s + stability fixes | ✅ |
| Stage 4 — tone melodies on D3 (knob, per-note detune, exponential tempo) | ✅ |
| Stage 5 — Python converter, 7 song clips (`sounds.h`), previews approved | ✅ |
| Stage 6 — clip playback (varispeed, drift, seamless loops, loudness matching), text → phrase interruption | ✅ (text/phrase part later replaced by the HACK button) |
| Stage 7 — own Wi-Fi `DFAB-ESP32` + captive portal, start without waiting | ⚠️ code done, **hardware test outstanding** (§0) |
| HACK button — 7 knob songs + 7 HACK songs (replaces the text → phrase interruption and the tone player); `sounds/` split into `Regular Songs/` + `Hack Songs/`, `clips.csv` with `role` | ⚠️ code done + simulated, **hardware test outstanding** (§0) |
| Stage 8 — integration (battery run, grounds, final README) | ⚠️ open |
| Volume | ⚠️ soft; hardware options in §8.4 |
| Phone hotspot / `dfab-esp32.local` on Android | superseded by Stage 7 (own network, fixed address) |

---

## 4. Pitfalls & learnings

### 4.1 Nano ESP32 serial ports (biggest time sink)
- `Serial` = USB. `Serial0` = UART on **D0/D1**. `Serial1`/`Serial2` have **no default header pins** — you must pass pins.
- The silkscreen **"TX1"/"RX0"** on the Nano ESP32 are **D1/D0 = Serial0**, *not* Serial1. A sketch using `Serial1.begin(9600)` with a wire on "TX1" sends nothing on that wire.
- Use **D-labels**, not raw GPIO numbers or `RX1/TX1` macros: with *Tools → Pin Numbering → By Arduino pin (default)*, raw GPIO numbers get re-interpreted as Arduino pin numbers. `D9, D8` is unambiguous.
- Avoid `Serial0` on D0/D1: carries boot messages, and an arduino-esp32 issue (#9662) reports a reboot loop with `Serial0.begin()` on Nano ESP32.

### 4.2 Logic levels
- ESP32 pins are 3.3 V only. Anything 5 V into an ESP32 pin (R4 TX, HC-SR04 echo) needs a divider: **1 kΩ series + 2 kΩ to GND** (≈ 3.33 V; 10 k/20 k or 1 k/2.2 k also OK). A divider only works for 5 V → 3.3 V.
- ESP32 3.3 V into an R4 input is **out of spec** (R4 HIGH ≈ 3.5–4 V) but harmless and has worked one-way so far. If garbled: use a **BSS138 bidirectional level-shifter module** (LV = ESP32 3V3, HV = R4 +5V, shared GND).
- Alternative not pursued: R4's Qwiic connector is 3.3 V logic (I²C) — no shifter needed, but more complex code.

### 4.3 Wiring
- **Always wire GND ↔ GND between boards.** On a shared laptop it works without (USB grounds are common), then fails on battery.
- Arduino docs disagree on Nano R4 D0/D1 (user manual vs schematic). If nothing arrives, swap the wire to R4 D1.
- Never connect 5V/VBUS/3V3 rails between the two boards when each has its own USB power.

### 4.4 Arduino IDE
- With two boards plugged in, **check Tools → Board and Tools → Port in every sketch window** (IDE 2 remembers per window). `WebServer.h: No such file or directory` = sketch compiled for the R4, not the ESP32.
- Don't install a "WebServer" library from Library Manager — the real one ships with the ESP32 board package.
- If a compile/upload fails, the board keeps running the **old** sketch — easy to miss.
- Own header files in the sketch folder: `#include "secrets.h"` (**quotes**). `#include <secrets.h>` (angle brackets) only searches libraries/board package → `fatal error: secrets.h: No such file or directory` even though the file is there (✅ reproduced 2026-11-26).

### 4.5 Wi-Fi
- Campus networks (eduroam) usually block device-to-device traffic → use ESP32 access point or a phone hotspot.
- **ESP32 access point:** "connected, no internet" is normal. Phones route around it via mobile data → type `http://` explicitly, turn off mobile data / Wi-Fi Assist, VPNs, iCloud Private Relay. Test: airplane mode → Wi-Fi only.
- **Phone hotspot:** ESP32 is **2.4 GHz only** (iPhone: *Maximize Compatibility* ON; Android: band 2.4 GHz). Phone assigns a changing IP → use `http://dfab-esp32.local` (mDNS: works on Mac/Windows/iPhone; many Android browsers don't support `.local`). Phones stop advertising idle hotspots (keep iPhone's Personal Hotspot screen open; disable Android auto-off).
- `WiFi.setSleep(false)` after connecting avoids sluggish replies in station mode.
- **Credentials are hard-coded in the sketch — remove before sharing code.** (Redacted in this doc.)
- Security: WPA2 either way; the password strength is what matters. Once the stepper is driven over Wi-Fi, keep the driver's 12 V supply physically within reach as the emergency stop.

### 4.6 Power bank
- Plug into each board's **USB-C**, not VIN (bank gives 5 V; VIN needs ≥ 6 V).
- Power banks auto-shut-off at low current; trickle mode only lasts ~2 h. Test by running 10–15 min.
- Plugging a second device into a multi-port bank can briefly drop all outputs → board reset. Plug both before starting.
- The bank must **not** power the stepper driver (needs 9–42 V) or the speaker circuit.

### 4.7 LEDs
- Nano ESP32: `LED_BUILTIN` = D13 = GPIO48 (yellow/orange). RGB LED = `LED_RED/LED_GREEN/LED_BLUE`, **active LOW**; some early boards have green/blue swapped.
- Nano R4: orange LED_BUILTIN reported non-working on some boards; RGB `LEDR/LEDG/LEDB` works (active LOW: `HIGH` = off).

---

## 5. ⚠️ Hazards to remember

1. **Speaker MOSFET circuit (user's breadboard diagram, 2026-11-26) — the current-limit resistor R3 is overloaded at 24 V.**
   - **Circuit as drawn by user:** ESP32 **D6** (⚠️ actually **D3**, see §8.3) → R1 100 Ω → gate of **20N06L** (logic-level N-MOSFET); R2 10 kΩ gate→source pull-down; source → GND; supply + → speaker → **R3 10–22 Ω, 2 W** → drain (all in series); C1 100 nF across the speaker; **no flyback diode yet**. The diagram is labelled **12 V** and "keep beeps short", but the user runs it at **24 V**. Only GND is shared with the ESP32. Sound: `tone(6, f)` = 50 % square wave.
   - **Worst-case numbers** (4 Ω speaker, 50 % duty, speaker treated as its DC resistance — real current is somewhat lower because the coil's inductance adds impedance at audio frequencies, but don't rely on that):

     | Supply | R3 | Peak current | Speaker (5 W rated) | R3 dissipation | Verdict |
     |---|---|---|---|---|---|
     | 24 V | 10 Ω | 1.71 A | 5.9 W | **14.7 W** | ❌ R3 (2 W) burns; speaker over rating; > breadboard ~1 A |
     | 24 V | 22 Ω | 0.92 A | 1.7 W | **9.4 W** | ❌ R3 (2 W) burns |
     | 24 V | 47 Ω | 0.47 A | 0.44 W | 5.2 W | ⚠️ needs ≥ 10 W resistor, gets hot |
     | 12 V | 22 Ω | 0.46 A | 0.43 W | 2.3 W | ⚠️ needs ≥ 5 W resistor |
     | 12 V | 47 Ω | 0.24 A | 0.11 W | 1.3 W | ✅ with 2 W resistor (quiet) |
     | 5 V | 4.7 Ω | 0.57 A | 0.66 W | 0.78 W | ✅ with 2 W resistor |

   - **Recommended:** run the speaker branch from **12 V** (as the diagram intends) with R3 **22 Ω rated ≥ 5 W**, or 47 Ω / 2 W if quieter is acceptable. At 24 V, R3 must be ~47 Ω and rated ≥ 10 W — wasteful and hot.
   - **Add the flyback diode** (1N4001 or 1N5819) across the speaker, cathode (stripe) to the + side, as the diagram notes.
   - At 3.3 V gate drive the 20N06L is only partly on (logic-level parts are usually specified at 4.5–5 V) — check it stays cool.
   - Long tones / continuous playback = continuous dissipation; **"silence" must be MOSFET OFF (0 % duty), not 50 % duty.**
   - Cleaner long-term alternative: amplifier module at 5 V (class-D, or I²S amp e.g. MAX98357A for sound files).
2. **Stepper driver:** never connect/disconnect motor wires while powered. Don't use Dupont pins in the screw terminals for 1.5 A — use stranded wire/ferrules.
3. **Pots:** wire pot VCC to **3V3** on the ESP32, never 5 V. ❌ **Found 2026-11-26: all three pot VCCs were on VBUS (5 V)** → wiper can put up to 5 V on A0–A2 (abs. max ≈ 3.6 V). Rewire to 3V3 before Stage 1 test; the full-sweep test shows whether a pin was damaged.

---

## 6. File inventory

Files in `DFAB_Bridge/` (current):

| File | Board | Status |
|---|---|---|
| `esp32_wifi_to_r4/esp32_wifi_to_r4.ino` | ESP32 | **Current (Stage 7 + HACK button).** Own Wi-Fi + captive portal, HACK page (`/`, POST `/hack`, `/status`), pots (A0–A2), slider link to R4, clip player (8 kHz timer interrupt + LEDC 40 kHz on D3): 7 knob songs + 7 HACK songs. Compiles (2 599 977 B, 82 %). |
| `esp32_wifi_to_r4/melodies.h` | ESP32 | Old tone melodies (Stage 4). **No longer included** by the sketch since the HACK change; kept for reference. |
| `esp32_wifi_to_r4/sounds.h` | ESP32 | **Generated** by `python/convert_sounds.py` — never edit; git-ignored (copyrighted audio). 3.6 MB of text. |
| `esp32_wifi_to_r4/secrets.h` | ESP32 | Old hotspot credentials, **unused since Stage 7**; git-ignored. Never share. |
| `r4_message_received/r4_message_received.ino` | R4 | **Current, Stage 3 + fixes.** Receiver (`S/W` lines; still prints other lines as text, but the ESP32 no longer sends any), AccelStepper speed mode with own ramp, dwell reversal, ENA idle-off, failsafe, non-blocking status line (`target_s`, `steps_s`, `maxgap_us`, `rx`, `bad`). Needs AccelStepper. |
| `pot_test/pot_test.ino` | ESP32 | Pot wiring test (raw values + mV), no Wi-Fi. |
| `python/convert_sounds.py` | Laptop | Sound converter (Stage 5/6): `clips.csv` → `sounds.h` + `python/preview/*.wav`. Windows `.venv\Scripts\python python\convert_sounds.py`, macOS `.venv/bin/python python/convert_sounds.py`. Options `--report-only`, `--csv`, `--out`, `--preview-dir`. |
| `python/send_command.py` | Laptop | ⚠️ Empty (0 bytes). |
| `python/preview/` | Laptop | Generated WAV previews (`channel_…`, `hack_…`); git-ignored. Subfolders `square_test/`, `hack_tone_test/` = rejected test previews, safe to delete. |
| `sounds/Regular Songs/`, `sounds/Hack Songs/`, `sounds/clips.csv` | Laptop | User's song files (git-ignored), sorted by role + clip list `file,name,role,start,length_s` (row order = knob / HACK order). |
| `.venv/` | Laptop | Python 3.13 venv (numpy, scipy, soundfile, librosa) — Windows PC only so far; git-ignored. |
| `.gitignore`, `../.gitignore` | — | `.venv`, audio, `sounds.h`, previews; `secrets.h` (group_05 level). |

Older files mentioned in earlier sessions (`esp32_hotspot_to_r4.ino`, the AP-version `esp32_wifi_to_r4.ino`, `r4_receiver_led.ino`,
`esp32_bridge.ino`, `r4_receiver.ino`) are **not in this folder** and obsolete. `../mike/` holds an old copy of the Stage 0
sketches (its ESP32 sketch does not compile — missing `#include "secrets.h"`).

### Stepper driver settings (from photo of driver label — verify against your unit)
- ⚠️ **2026-11-26: user's driver was found at SW1–6 = ON ON OFF ON ON OFF = full step (200 pulses/rev) + 1.5 A.** Sketch assumes 1/8 (1600) → advised SW1 → OFF (final OFF ON OFF ON ON OFF), power off while switching, check against the label on the unit.
- Current **1.5 A** (peak 1.7): SW4 ON, SW5 ON, SW6 OFF. (1.0 A runs cooler: SW4 ON, SW5 OFF, SW6 ON.)
- Microstep **1/8 = 1600 pulses/rev**: SW1 OFF, SW2 ON, SW3 OFF. (Full step loudest; 1/8 smoother.)
- Signal wiring (common-cathode): PUL−, DIR−, ENA− → R4 GND; PUL+ → R4 step pin; DIR+ → R4 dir pin; ENA+ unconnected (= enabled).

---

## 7. Next steps (planned) — original plan, kept for reference

> Historical: written before the stages were built. Several details changed (speaker on D3 not D6, own Wi-Fi instead of the hotspot, stepper pins D7/D5/D3, 4800 steps/s, varispeed clips). Current state: §0; decision log: §8.

Goal:
- **Nano ESP32** reads **3 potentiometers** (2 slides + 1 knob), plays sound on the speaker, keeps Wi-Fi, and sends slider values to the R4.
- **Nano R4** rotates the stepper: speed set by the speed slider, direction alternating with a dwell time set by the detune slider.

### 7.1 Decisions (user, 2026-11-26)
| Topic | Decision |
|---|---|
| Speaker | **ESP32 drives it** through the user's existing **MOSFET** circuit. Tones + detuning already tested and working. |
| Sound content | **Now: tones.** **Eventually: sound files** that get detuned. |
| Distortion | **Detuning.** |
| Pots (two **separate** slide pots + one knob) — **pins updated by user** | **A2 = detune slide** (was A6) · **A1 = speed slide** (was A4) · **A0 = knob, channel / song choice** (was A2). All three are ADC1 → work with Wi-Fi on. (A2 = GPIO3 is a strapping pin; fine in practice, A3 is the spare if it ever misbehaves at boot.) |
| Pot behaviour in sound | Defined by user in the Arduino sketch (two slider values change the sound behaviour). |
| Stepper speed | **Follows the speed slider (A1).** |
| Stepper direction | **Alternates**; the **detune slider (A2)** sets the **delay (dwell) before each direction switch**. |
| Wi-Fi | **Kept in final build** — planned use: select the song over Wi-Fi, freeing the knob (A0) for another function later. |
| Pitch / tempo | **Option C preferred ("at best"): independent pitch and tempo.** |
| Sound-file preparation | **Workflow requirement: all conversion / processing of sound files is done externally in Python on the laptop; the Arduino only reads the prepared output** (see §7.4). |
| Audio quality | **Rough PWM audio through the existing MOSFET circuit is accepted** (no amp module for now). |
| Speaker supply | User currently runs the MOSFET circuit at **24 V** with series/parallel resistors → see §5 (R3 overloaded; move to 12 V or upsize R3). |
| Stepper parameters | Code must expose **clearly named placeholder variables** the user replaces later (see §7.6). |

### 7.1b Notes on the decisions / still open
1. **Option C with tones is free** (detune = frequency multiplier, speed = tempo multiplier). **With sound files**, independent pitch/tempo is done **offline in Python** (§7.4) by pre-computing variants — at the cost of discrete steps and more storage — instead of real-time granular processing on the ESP32.
2. **PWM audio through the MOSFET:** accepted rough quality. Carrier must be ultrasonic (≥ ~40 kHz); exact LEDC frequency/resolution to be chosen at build time.
3. ⚠️ **Speaker circuit at 24 V overloads R3 (2 W) by ~5–7×** — fix before long tests (§5).
4. **Stepper ranges** — user will fill the placeholder variables (§7.6).
5. **Knob (A0) future function** once Wi-Fi selects the song — TBD.

### 7.2 Phase A — fix current open issues first
- Report result of the LED diagnostic (3 flashes?).
- On power bank: confirm GND wire between boards, use `dfab-esp32.local`, check R4 RGB flash on receipt.

### 7.3 Phase B — pots on the ESP32
- Wiring per pot: outer pins → **3V3** and **GND** (never 5 V), wiper → **A0 (knob), A1 (speed slide), A2 (detune slide)**.
- HW-233 slide pot: use one output (OTA) per slider; its VCC pin → 3V3.
- Read 0–4095 (12-bit). Smooth (average 8–16 samples) and use a **deadband** (ignore changes < ~20 counts) so values don't jitter.
- First test: print the three values to the Serial Monitor.
- Knob → channel index: divide range into N zones with hysteresis so it doesn't flicker at a boundary.

### 7.4 Phase C — sound on the ESP32
- **Now:** tones through the existing MOSFET circuit on **D6** (non-blocking, `millis()`-based note scheduler, no `delay()`); detune = frequency multiplier from A2, tempo = multiplier from A1 → independent (option C).
- **Later:** sound files played as PWM audio (ESP32 LEDC, duty = sample value) through the same MOSFET. Rough quality accepted.

#### Workflow requirement — sound files are prepared in Python, read by Arduino
All conversion happens on the laptop in Python; the ESP32 only plays ready-made data.

1. **Input:** source audio (`.wav` / `.mp3`) in a `sounds/` folder; one file = one channel (selected by knob A0 or Wi-Fi).
2. **Python conversion script** (to be written): mono → resample (8–16 kHz) → normalise → **8-bit unsigned PCM** (matches PWM duty resolution).
3. **Optional offline effects (for option C with files):** pre-compute pitch-shifted and/or time-stretched variants at a few fixed steps (e.g. detune −2…+2 semitones, speed 0.5×…2×) with a Python audio library (e.g. librosa). Trade-off: steps are discrete and storage multiplies (channels × pitch steps × tempo steps).
4. **Output:** one generated header file (e.g. `sounds.h`) with `const uint8_t` arrays + a table of name, sample rate and length per clip → copied into the sketch folder and `#include`d. No IDE plugins or SD card needed.
5. **Storage budget:** 8 kHz × 8-bit mono ≈ 8 KB/s → ~2 min per MB. The sketch's app partition (a few MB, depends on Tools → Partition Scheme) limits total length; check the size the compiler reports.
6. **Re-run** the script whenever sounds change; the Arduino side never needs to know how the data was made.

### 7.5 Phase D — ESP32 → R4 protocol
- Recommended: ESP32 sends the **raw slider values**, R4 does the stepper mapping (stepper logic stays where the motor is): e.g. `S1234 W2048\n` (S = speed slider A1, W = dwell/detune slider A2, both 0–4095).
- Send **on change** (after deadband), capped at ~10–20 messages/s, **plus a keep-alive every ~500 ms** (needed for the R4 failsafe).
- Wi-Fi song selection stays on the ESP32 (it plays the sound); nothing to send to the R4 unless the stepper should react to the song.

### 7.6 Phase E — stepper on the R4
- Wiring: R4 **D3 → PUL+**, **D4 → DIR+** (any free pins except D0/D1, which are Serial1), PUL−/DIR−/ENA− → R4 GND. Driver on 12 V. Motor coils A+/A−, B+/B− per multimeter.
- Behaviour: speed = map(S → 0 … max steps/s); every dwell time = map(W → min … max s) **ramp down → reverse → ramp up** (abrupt reversal at speed → missed steps/stall).
- Library: **AccelStepper** (`AccelStepper stepper(AccelStepper::DRIVER, 3, 4);`, `setMaxSpeed()`, `setSpeed(±steps/s)`, `runSpeed()` every loop). TB6600 clones are commonly quoted as needing ≥ 2.5 µs step pulses → `setMinPulseWidth(5)` (verify).
- **Loop must be non-blocking:** no `delay()`, no blocking `readStringUntil()`; read Serial1 char-by-char into a buffer; time the dwell with `millis()`. (The current `r4_message_received.ino` uses `delay(1000)` — must be rewritten.)
- **Failsafe:** if no message for ~2 s, ramp to 0.
- Start with a speed cap ≈ 1600–3200 steps/s at 1/8 microstep (1–2 rev/s), raise after testing.

#### Placeholder variables (user replaces values later — names to keep consistent in code)
| Variable | Meaning | Placeholder value |
|---|---|---|
| `STEP_PIN` | R4 pin → driver PUL+ | `7` (user wiring) |
| `DIR_PIN` | R4 pin → driver DIR+ | `5` (user wiring) |
| `STEPS_PER_REV` | Must match driver DIP switches | `1600` (1/8 microstep) |
| `SPEED_MIN_STEPS_S` | Speed at speed-slider minimum | `0` |
| `SPEED_MAX_STEPS_S` | Speed at speed-slider maximum | `1600` |
| `SPEED_STOP_THRESHOLD` | Slider value (0–4095) below which the motor stops | `100` |
| `DWELL_MIN_MS` | Time before direction switch at detune-slider minimum | `500` |
| `DWELL_MAX_MS` | Time before direction switch at detune-slider maximum | `10000` |
| `RAMP_STEPS_S2` | Acceleration used to slow down / reverse / speed up | `2000` |
| `MIN_PULSE_US` | Step pulse width for the TB6600 | `5` |
| `FAILSAFE_TIMEOUT_MS` | Stop if no message from ESP32 for this long | `2000` |
| `INVERT_DIRECTION` | Flip if the motor turns the "wrong" way | `false` |
| `ENABLE_PIN` | R4 pin → driver ENA+ | `3` (user wiring) |
| `ENA_DISABLES_WHEN_HIGH` | ENA polarity (most TB6600: HIGH = off) | `true` — verify on bench |
| `IDLE_DISABLE_MS` | Driver off after standing still this long | `3000` |

### 7.7 Phase F — integration
- Power: bank → both Arduinos (USB-C); 12 V → driver; speaker supply per §5. All grounds referenced correctly (Arduino GNDs common; driver signal GND to R4 GND; MOSFET speaker supply GND to ESP32 GND).
- Optional return path R4 → ESP32 (R4 D1 → 1 kΩ → ESP32 D9, 2 kΩ D9 → GND) for status/acknowledgements.

---

## 8. Interview answers & stage plan (2026-11-26)

### 8.1 Answers (user)
| Topic | Answer |
|---|---|
| LED diagnostic | ✅ 3 flashes → blink → solid. |
| Battery operation | ✅ works with GND wire. Phase A (§7.2) closed. |
| Hotspot phone | **Android** → `dfab-esp32.local` unreliable; recent Android versions may also change the hotspot address range. |
| Laptop OS | **macOS and Windows** (both). |
| ESP32 board package | **"Arduino ESP32 Boards" (by Arduino)**. ⚠️ Version number still needed (LEDC PWM / timer API differs between ESP32 core 2.x and 3.x). |
| Python | **Standalone Python 3 in VS Code** (not IronPython). |
| Python packages | **numpy, scipy, soundfile, librosa allowed.** User's own sound files; librosa only processes them. mp3 input needs ffmpeg. |
| Wi-Fi control in final build | **Phone browser page** (UDP sender kept as an extra). |
| Speaker supply | **12 V, R3 22 Ω ≥ 5 W.** |
| Flyback diode | **None available.** Real circuit differs from diagram → description/photo needed before sound stages. 1N5819/1N4001 still recommended. |
| Sound clips | Number/length **not decided**. The converter will print a storage report. |
| Pitch/tempo with files | **Independent (option C) via offline librosa variants.** |
| Stepper status | ✅ wired, DIP set, motor has turned. |
| Direction motion | **Continuous back-and-forth: run for dwell → ramp down → reverse → ramp up, no pause.** |
| ENA | **Switch the motor off via ENA after it has stood still for a set time** (slider at zero or failsafe). ENA is *not* used for reversing (motor would coast → jerk / missed steps). Heat comes from coil current whenever enabled, so idle-off is where ENA helps. User: **ENA+ on D3** → pin map to resolve. Polarity to verify on bench (on most TB6600 units, opto ON = disabled). |
| Holding torque | Not needed (free load). |
| Return path R4 → ESP32 | **No, keep one-way.** |
| Knob A0 zones | **= number of clips** (read from generated `sounds.h`). |

New placeholder variables for §7.6: `ENABLE_PIN` (user: `3` → conflicts with `STEP_PIN`), `ENA_DISABLES_WHEN_HIGH` (`true`, verify), `IDLE_DISABLE_MS` (e.g. `3000`).

### 8.2 Stage plan (✅ **approved by user 2026-11-26**, with Stage 7 extended to laptop)
Each stage ends with a hardware test by the user and approval before the next one starts.

| Stage | Content | Blocking inputs from user |
|---|---|---|
| 0 Housekeeping ✅ (hardware test passed, phone + laptop) | Credentials → `secrets.h`; each `.ino` in a same-named folder; `.gitignore`; README update. | — |
| 1 Pots on ESP32 ✅ (hardware test passed) | A0/A1/A2 with smoothing + deadband; Wi-Fi bridge kept; test in Serial Plotter. | **Pot VCC moved from VBUS to 3V3** (§8.3) |
| 2 Board link ✅ (hardware test passed) | ESP32 sends `S#### W####` on change (≤ 20/s) + keep-alive every 500 ms; new non-blocking R4 receiver (no motor yet). | — |
| 3 Stepper ✅ (hardware test passed; DIP set to 1/8) | AccelStepper, §7.6 placeholders + ENA idle-off, ramp reversal, 2 s failsafe; low speed cap first. | ENA polarity bench test; PUL−/DIR−/ENA− wiring; install AccelStepper |
| 4 Tones ✅ (hardware test passed) | Non-blocking melody player on **D3** (LEDC direct, not `tone()`); detune = random per-note offset up to ±200 cents; speed = tempo ×0.67…×1.5 (exponential); knob = 8 melodies (`melodies.h`). | — |
| 5 Python converter ✅ (previews approved by user) | `python/convert_sounds.py`: `sounds/clips.csv` → cut chorus → 8 kHz 8-bit → `esp32_wifi_to_r4/sounds.h` + storage report + WAV previews. **Varispeed mode** (`TEMPO_STEPS = 1`); tempo variants still possible. | Preview check (user) |
| 6 File playback ✅ (hardware test passed) | Clips via 8 kHz timer interrupt → LEDC 40 kHz 8-bit on **D3**, varispeed ×0.67…×1.5 with linear interpolation, detune = slow drift (new random target every 500 ms, glide), knob = 7 clips + phrase; **any web/UDP text → phrase once per message (queue ≤ 10) → clip restarts from its beginning**, text still forwarded to R4. **No pause (`REPEAT_PAUSE_MS = 0`): clips loop seamlessly inside the timer interrupt; phrase repeats at once.** | — |
| 7 Phone + laptop page ✅ code done, ⏳ hardware test | **ESP32's own open Wi-Fi "DFAB-ESP32" (no hotspot)** + captive-portal pop-up, fixed address `http://192.168.4.1`; visitors can send messages; start-up never waits for Wi-Fi; typed text sanitised, ≤ 55 bytes, prefixed `TXT ` for the R4. | — |
| 8 Integration | Full battery test, grounds per §7.7, final README. | — |

### 8.3 Answers after approval (user, 2026-11-26, night)
| Topic | Answer / consequence |
|---|---|
| ESP32 core | **Stay on "Arduino ESP32 Boards" 2.0.18-arduino.5** (installed on Windows PC; verified its LEDC API is the 2.x one: `ledcSetup`, `ledcAttachPin`). ⚠️ Mac must have the same version. |
| Stepper pins (R4) | ✅ **PUL+ = D7, DIR+ = D5, ENA+ = D3.** Replaces §7.6 placeholders: `STEP_PIN 7`, `DIR_PIN 5`, `ENABLE_PIN 3`. Conflict resolved. ✅ PUL−/DIR−/ENA− on R4 GND (user). |
| Speaker circuit | Same as drawn in §5 **except: no capacitor C1, R3 = 100 Ω, gate driven from ESP32 D3 (not D6, user 2026-11-26)** (replaces the 22 Ω of §8.1). Still no flyback diode. At 12 V: peak ≈ 0.115 A; R3 ≈ 0.66 W at 50 % duty, **1.3 W if the MOSFET is stuck on** → R3 should be rated **≥ 2 W**. Speaker gets ≈ 0.03 W → much quieter than with 22 Ω (≈ 12 dB). ✅ Supply 12 V. ✅ R3 rated **2–5 W** (judged by length) → OK for 0.7 W typical / 1.3 W worst case. |
| Pots | Added to the same breadboard, wipers on **A0 (knob), A1 (speed), A2 (detune)**. ❌ **VCC was on VBUS (5 V)** → must move to **3V3** (§5 hazard 3). GND → ESP32 GND. |
| Stage 7 | Page must also work from the **laptop**. Interpreted as: same ESP32-served page, usable in a laptop browser. ✅ Confirmed: the ESP32 page works from the laptop (tested in Stage 0). |
| Found in Stage 0 | `../mike/esp32_wifi_to_r4/` holds an identical sketch that **does not compile** (no `#include "secrets.h"`); its `secrets.h` is now git-ignored too. `python/send_command.py` is empty. |

### 8.4 Stage notes
- **Stage 1 (✅ 2026-11-26):** first test showed no movement — fixed by the user (wiring); `pot_test/pot_test.ino` written for that diagnosis. Pots now on 3V3. ESP32-S3 ADC saturates at ≈ 3.1 V, so the last few % of travel read 4095 (normal).
- **Stage 2 protocol (final):** `S<0..4095> W<0..4095>
` (ESP32 `println`). R4 treats lines starting `S`+digit as slider lines (strict parse, else `bad`++); everything else = text (web page/UDP). ~~Typing `S100 W200` on the web page also sets values~~ → closed in Stage 7: typed text is sent as `TXT <text>`. UART load ≤ 20 × 13 B/s ≈ 27 % of 9600 baud.
- **Stage 2 first test (2026-11-26): ❌ R4 `link:0`, solid red, no `text:`/`bad line:`** while the ESP32 ran fine (Wi-Fi, pots) → nothing readable reaches R4 D0. Added `rx:` byte counter to the R4 status line to separate "no bytes" (wiring) from "garbled bytes" (level). Result: `rx` rises only on web-page text → wiring OK, **ESP32 not sending slider lines → most likely still running the Stage 1 sketch** (code on disk is correct). Check: ESP32 start-up line must read `… (Stage 2: pots -> R4)`.
- **Upload error (2026-11-26):** `Failed to retrieve language identifiers` / `error get_status: LIBUSB_ERROR_TIMEOUT` / `exit status 74` = dfu-util timeout. Nano ESP32 uploads use **no 1200-baud reset** (`use_1200bps_touch=false` in boards.txt): the *running sketch* must hand over to the bootloader. Fix: **double-tap reset → bootloader mode (RGB LED pulses) → re-select Port → Upload**; close Serial Monitor/Plotter; direct USB port. Suspected (unverified) trigger: Stage 1 sketch printing 50 lines/s over USB → `PRINT_POTS` now defaults to `false`.
- **Stage 2 result (2026-11-26):** ✅ upload fixed (double-tap), ✅ failsafe works. ❌ `http://dfab-esp32.local` not working. Assessment: sketch side was minimal but correct (`MDNS.begin` after connect, `setSleep(false)`); added return-value check + start-up message and `addService("http","tcp",80)`. Most likely causes are outside the sketch: client not on the hotspot (Claude's check: the Windows PC was on **eduroam** at the time), Android browser `.local` support, Android hotspot not forwarding multicast. Proper fix belongs to Stage 7.
- **Stage 2 ✅ (2026-11-26):** all checks passed; the `.local` failure was the laptop being on the wrong Wi-Fi.
- **Stage 3 design (2026-11-26):**
  - AccelStepper's own acceleration only works in position mode (`moveTo`/`run`), so speed mode uses `runSpeed()` + a **linear ramp in the sketch** (every 1 ms, Δt capped at 5 ms so a slow loop never causes a speed jump).
  - **Dwell = time at full speed**: timer starts when the target speed is reached, so one reversal cycle = dwell + 2 × (speed / `RAMP_STEPS_S2`) (e.g. 0.5 s + 1.6 s at 1600 steps/s). While the target is 0 the timer is reset → after a stop the motor keeps its direction and runs a full dwell.
  - ENA: driver starts **off**, switches on as soon as a non-zero speed is requested (first step ≥ ~30 ms later because the ramp starts at 0), off after `IDLE_DISABLE_MS` at standstill.
  - Python simulation of `updateMotion()` (Claude's scratchpad, not kept) found and fixed: direction flipping while stopped / immediate reversal on restart.
  - Not handled (accepted): TB6600 wants DIR ≥ 5 µs before the PUL edge; AccelStepper writes DIR right before the pulse. Only affects the first microstep after a reversal, at near-zero speed.
- **Stage 3 ✅ (2026-11-26):** all checks passed at 1 rev/s (ENA polarity `true` correct, unless the user changed it).
- **Speed increase to 2–5 rev/s (user question, guidance given, estimates not measured):** 1/8 → 2/3/5 rev/s = 3200/4800/8000 steps/s; raise `RAMP_STEPS_S2` with it (rule: = `SPEED_MAX_STEPS_S` → 1 s ramp). 17HS4401 at 12 V/1.5 A (≈ 2.8 mH): torque falls noticeably from ≈ 5–7 rev/s → 5 rev/s plausible unloaded, little reserve. TB6600 pulse limit ≈ 13–20 kHz (OK). Weak point = R4 loop timing (`runSpeed()` polling; USB status print stalls) → `PRINT_STATUS = false` above ≈ 3 rev/s. Fallbacks: 1/4 microstep (800/rev, halve step numbers) or 24 V for the driver only. Clamp motor, secure shaft load. Offered (not done): rev/s-based settings, loops/s counter.
- **Unstable speed reading (2026-11-26) — causes & fixes:**
  1. ESP32 pot noise passes the deadband: Wi-Fi TX spikes and short 3V3 dips (ESP32 ADC measures against an internal reference, so a pot on 3V3 is *not* ratiometric). Simulation with an assumed noise model: still slider changed value 140–690×/min → **added `POT_SMOOTHING = 4`** (exponential moving average, ≈ 0.3 s lag) → 2–14×/min. Optional hardware fix: 100 nF wiper → GND per pot.
  2. `steps_s` is the *ramping* speed — it always swings during reversals. Added `target_s` (what the slider asks for).
  3. R4 USB print **can wait** (confirmed in `renesas_uno/1.6.0/cores/arduino/usb/SerialUSB.cpp`: busy-waits while the 256-byte TX buffer is full; each `print` = one flush). Now one `snprintf` line, sent only if `availableForWrite()` has room → never waits. Added `maxgap_us` (longest `loop()` pause per status line).
- **4800 steps/s (3 rev/s):** driver DIP unchanged (1/8, 1.5 A: OFF ON OFF ON ON OFF). `SPEED_MAX_STEPS_S = 4800`, `RAMP_STEPS_S2 = 4800`. Simulation (loop durations assumed): reversal every 2.5 s at min dwell (2 s ramp + 0.5 s); old print could cause 1.7 ms step gaps, new ≤ 0.28 ms; real speed ≈ 95 % of commanded (AccelStepper `runSpeed()` doesn't make up late steps — steady, not unstable).
- **Stability fix + 4800 ✅ (2026-11-26):** all checks passed on hardware.
- **Stage 4 design (2026-11-26):**
  - `tone()` in core 2.0.18 = queue + task that `delay()`s for the note length → live pitch changes lag and a full queue blocks `loop()` → player drives **LEDC directly** (`ledcSetup/ledcAttachPin` in `setup()`, `ledcWriteTone(ch, f)`; `f = 0` → 0 % duty = MOSFET off). Frequency only re-set when it changes (re-config can click). `ledcAttachPin` is pin-remapped by the core (`io_pin_remap.h`), so `D3` is correct.
  - User's choices: detune = **each note randomly sharp/flat, new every time, amount 0…200 cents** (slider bottom = in tune; applied live while a note sounds). Tempo = **exponential ×0.67…×1.5** (`TEMPO_MIN/MAX`; middle = √(MIN·MAX)). Knob = **8 melodies**, zones with 60-count hysteresis. Melody keeps playing when the motor stops (not asked; easy to change).
  - User's `sketch_nov26a` notes: unfinished `wrap_freq()`, missing `#include "pitches.h"`, `remap()` ignores `omin` (`map()` does what was intended). Timing copied: quarter slot 325 ms, 77 % sounding.
  - Python check (Claude's scratchpad: `sim_sound.py` parses the real `melodies.h` + sketch constants): all notes in order, gaps/pause silent, tempo/detune ranges as specified, knob sweep clean, 0 flicker with ±40 noise at borders. WAV previews rendered for ear-checking.
  - Copyright: only public-domain tunes written from memory; copyrighted songs only from notes/MIDI the user provides.
- **Stage 5 (2026-11-26):**
  - User chose real audio clips (option B) of 7 copyrighted songs, sourced by the user (full songs in `sounds/`, 1–3.5 min each). Claude does not transcribe copyrighted melodies; the user is responsible for the files. **mp3s, `sounds.h` and previews are git-ignored** (shared course repo).
  - User's choices: first 5 pitch-kept tempo variants at 8 kHz, 7 s clips. Then the user's chorus times (14–19 s, 113 s total) needed 4.69 MB → **final choice: varispeed, 8 kHz, full lengths** (one copy per clip; ESP32 changes the playback rate, pitch follows tempo). Knob = **7 clips + the tone phrase "Du bist gut genug"** (8 zones). Detune = live random warble (Stage 6).
  - Chorus times (user): Rick 0:01–0:18, Harlem Shake 0:15–0:29, Gangnam 1:05–1:21, All Star 0:00–0:19, Buttercup 0:16–0:33, Curb 0:00–0:14, Baby Shark 0:10–0:26.
  - **Real conversion ✅ (Claude):** 904 000 B (43 % of 2.1 MB budget), 7 arrays, lengths match, no clipped samples, fades to 128. **Fit check: sketch + `sounds.h` = 1 695 685 B (53 %).** Loudness differs (RMS 0.12 All Star … 0.32 Baby Shark, peak-normalised) → if uneven by ear: `DRIVE = 2.0` or add RMS matching. `sounds.h` = 3.6 MB of text: opens as a tab in Arduino IDE (may be slow).
  - Storage: app partition 3 145 728 B. (Test with 5 variants × 7 s: 2.04 MB data → 2 827 345 B total, 89 %.) The 9 MB FAT partition is not used (would need a separate upload tool) — option if more audio is ever needed.
  - Python env: `DFAB_Bridge/.venv`, **Python 3.13** via `uv` (3.14 is the system default; numba/librosa support for 3.14 not verified). numpy 2.5.5, scipy 1.18.1, soundfile 0.14.0 (libsndfile 1.2.2, decodes mp3), librosa 1.0.1, numba 0.68.1. macOS: `uv venv .venv --python 3.13` (or `python3.13 -m venv .venv`), then `.venv/bin/pip install numpy scipy soundfile librosa`.
  - Tested by Claude with placeholder start 0:30 for all clips (outputs in scratchpad, not the project): 35 arrays, table lengths match, values 3–253, fades end at 128, chroma similarity of variants to ×1.00 = 0.94–1.00 (pitch kept), ~23 s run time.
  - ⚠️ For Stage 6: PWM audio idles at 50 % duty (sample 128) while a clip plays → R3 ≈ 0.66 W continuously (OK for 2–5 W); between clips the player must go to 0 % duty.
- **Stage 4 ✅ / Stage 5 ✅ (2026-11-26):** melody player confirmed on hardware; preview cuts confirmed by ear.
- **Stage 6 design (2026-11-26):**
  - User idea: **any text input plays "Du bist gut genug", then the song comes back.** User's choices: clip **restarts** from its beginning; extra messages are **queued** (one phrase each, `MAX_QUEUED_PHRASES = 10`, more are dropped); text **still forwarded** to the R4; clip detune = **slow drift** (`WARBLE_MS = 500`). Knob moved during the phrase → the new zone starts after it.
  - Sample clock: hardware timer 0 (`timerBegin(0, 80, true)`, alarm 125 µs = `1e6 / SOUND_SAMPLE_RATE`). `timerAttachInterrupt` in core 2.0.18 registers with flags 0 (not an IRAM interrupt) → masked while flash cache is off, so reading `sounds.h` from flash and calling `ledcWrite()` inside it is safe. ISR runs on the same core as `loop()`, so no true concurrency with the loop's PWM changes.
  - One LEDC channel, two modes: clips = `ledcSetup(ch, 40000, 8)` + `ledcWrite(sample)`; phrase = `ledcWriteTone()` (10-bit). `ledcSetup` only reconfigures the timer, the pin stays attached (checked in `esp32-hal-ledc.c`).
  - Position = 12 fraction bits (`4096` = 1 sample): longest clip 19 s × 8000 × 4096 ≈ 6.2e8 < 2^32.
  - Python simulation (`sim_stage6.py`, scratchpad; real `sounds.h` lengths + real phrase): clip length 25.38 / 16.95 / 11.33 s at slider bottom/middle/top (= 17 s ÷ tempo), 2 s pause, MOSFET off in every pause and phrase gap; text → phrase at once, clip restarts after 3.4 s; 3 texts → 3 phrases back to back; 15 texts → 11 phrases (limit); knob change during phrase → new clip after it; 8 knob zones in order. Found & fixed: drift could overshoot / jump after a pause → glide position capped, new glide starts at the current pitch. After fix: max 0.76 cents/ms while sounding.
  - Note: middle tempo = √(0.67 × 1.5) = ×1.0026 (not exactly 1); `TEMPO_MIN = 0.6667` would make it exact.
- **Stage 6 change (user): no delay between loops.** `REPEAT_PAUSE_MS = 0` → `clipLoop`: the ISR wraps the read position (`pos -= length`) instead of stopping, so no 0 %-duty step (would click: 0 % → 50 % duty is a DC jump). Simulation: 0 ticks at 0 % duty over 60 s at all speeds; phrase repeats every 3.403 s. Known: a DC pop can still occur when a clip *starts* (knob change, after the phrase) — a 20 ms duty ramp would remove it if it bothers.
- **Volume (user: too soft) — options outlined 2026-11-26, nothing changed yet.** Now: 12 V / (100 Ω + 4 Ω) = 0.115 A peak → ≈ 0.03 W into the speaker. Per R3 (12 V, 50 % duty; clips average 50 % duty continuously):

  | R3 | Peak current | Louder by | R3 while playing | R3 if MOSFET stuck on | Needs |
  |---|---|---|---|---|---|
  | 100 Ω (now) | 0.115 A | — | 0.66 W | 1.3 W | ≥ 2 W ✅ |
  | 2 × 100 Ω parallel = 50 Ω | 0.22 A | +5.7 dB | 1.2 W (0.6 W each) | 2.5 W (1.2 W each) | each ≥ 2 W |
  | 47 Ω | 0.235 A | +6.2 dB | 1.3 W | 2.6 W | ≥ 5 W |
  | 4 × 100 Ω parallel = 25 Ω | 0.41 A | +11 dB | 2.1 W (0.5 W each) | 4.3 W (1.1 W each) | each ≥ 2 W |
  | 22 Ω | 0.46 A | +12 dB | 2.3 W | 4.7 W | ≥ 5 W, gets hot |

  Free: speaker in a box/baffle (bare cone cancels its own bass), converter `DRIVE = 2…3` + loudness matching (clips only, distorts peaks). Lower R3 → add the flyback diode (1N5819/1N4001, stripe to +12 V). Best: PAM8403 class-D module at 5 V (RC low-pass + input divider from D3), speaker on its bridged output.
- **Volume option 2 done (2026-11-26): loudness matching in the converter** (replaces `DRIVE`). Per clip: high-pass 150 Hz (`HIGHPASS_HZ`, 0 = off; benefit is theoretical — small speaker can't play deep bass) → scale so the RMS of the louder half (50 ms windows) = `LOUDNESS` → `tanh` soft limiter → ×0.99 → fade. Measured before choosing: target 0.25 / 0.35 / 0.45 → ~0.1 / 1.4 / 4 % of samples rounded; loud clips are already at the ceiling. **Chosen `LOUDNESS = 0.45`:** vs plain peak normalisation All Star +8.4 dB, Never Gonna +4.8, Curb +3.8, Gangnam +1.2, Buttercup +1.2, Harlem +0.3, Baby Shark −0.4 dB. Verified in `sounds.h`: spread 8.9 dB → 0.21 dB, no samples at 0/255, ends at 128; sketch compiles (54 %). For more volume overall: hardware (R3 table / baffle / PAM8403).
- **Stage 6 ✅ (2026-11-26):** all checks passed on hardware (incl. seamless loops, loudness matching).
- **Stage 7 (2026-11-26):**
  - User's choices: start at once without Wi-Fi ✅; visitors may send messages; first "keep the phone hotspot" — Claude flagged that visitors would then need the hotspot password (+ mobile data, ~10 devices) and a changing IP → **user chose: only the ESP32's own Wi-Fi.**
  - `startNetwork()`: `WiFi.mode(WIFI_AP)`, `softAPConfig(192.168.4.1)`, `softAP("DFAB-ESP32", open, channel 6, max 8 clients)` (core default would be 4; ESP32 max 10). `AP_PASSWORD` ≥ 8 chars → WPA2. `DNSServer` answers every name with 192.168.4.1; `server.onNotFound()` → 302 to `http://192.168.4.1/` → Android "Sign in to network" / iOS sheet / Windows browser pop-up. mDNS kept for laptops.
  - **Resolves the open Wi-Fi-blocking issue**: no `connectWiFi()` wait loop / `ESP.restart()` any more; pots, sound and motor run ~3 s after power-up (3 flashes + 1.5 s Serial delay) with or without clients. LED on = network running.
  - Visitor safety: text → control characters to spaces, cut to 55 bytes, sent as `TXT <text>` (R4 sees `T`, never a slider line; 4 + 55 = 59 < 63-char R4 buffer). Queue limit 10 phrases still applies. Open network: anyone in range can trigger the phrase, nothing else.
  - `secrets.h` and the hotspot are no longer used (file kept, still git-ignored). Laptop/phone has no internet over this Wi-Fi while connected.
  - Compiles (1 705 229 B, 54 %). Not testable by Claude: captive-portal behaviour depends on the phone's OS/settings.
- At R4 start-up, one cut-off line (e.g. `text: 34 W2048`) can appear — the R4 joined mid-message. Harmless.
- ⚠️ **Open design issue (for Stage 7/8):** `connectWiFi()` blocks in `setup()` and restarts the ESP32 every 30 s without the hotspot → **no hotspot = no pots, no messages, no motor.** Decide later whether the installation must run without Wi-Fi (then make Wi-Fi non-blocking).

---

## 9. Sources consulted
- Arduino Nano ESP32 cheat sheet & full pinout — docs.arduino.cc/tutorials/nano-esp32/cheat-sheet, docs.arduino.cc/resources/pinouts/ABX00083-full-pinout.pdf
- Arduino Nano ESP32 datasheet (VIN, 3.3 V pins) — docs.arduino.cc/resources/datasheets/ABX00083-datasheet.pdf
- Arduino Nano R4 datasheet / product page (5 V GPIO, Qwiic 3.3 V) — docs.arduino.cc/hardware/nano-r4
- Nano ESP32 / Nano R4 pinout write-ups — deepbluembedded.com, esp32.co.uk
- RA4M1 3.3 V input threshold — element14 "Modifying the Arduino Uno R4: Making it 3.3V-Friendly"
- Serial0 reboot loop — github.com/espressif/arduino-esp32/issues/9662
- Pin numbering modes — support.arduino.cc (Select pin numbering for Nano ESP32)
- 17HS4401 specs — MotionKing / Handson datasheets
- Anker 533 (A1256) specs & trickle mode — service.anker.com; capacity test — blog.didierstevens.com (2025-04-16)
