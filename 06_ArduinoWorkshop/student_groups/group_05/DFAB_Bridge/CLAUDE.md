# MAS ETH DFAB — Arduino Nano ESP32 ↔ Nano R4 project

Read `README_Arduino_ESP32_R4_Bridge.md` in full before doing anything. §8 holds the latest
decisions and the stage plan; where §8 conflicts with earlier sections, §8 wins.

## Working rules (from the user)
- The user is an architectural designer (Python, GH_Python, learning C#). Explain hardware/C++ choices briefly.
- Be meticulous: check every proposal before handing it in. Never present unverified results as working.
  Say clearly what was compiled/tested and what was not.
- Be critical of requests that have problems; say so before implementing.
- Keep the system simple. Don't build complicated systems.
- Ask for context when instructions are unclear.
- **Work in stages (README §8.2). After each stage: stop, report what to test on hardware, wait for approval.**
- Prefer multiple-choice questions with a free-answer option when interviewing the user.

## Project facts that are easy to get wrong
- Nano ESP32 pins are 3.3 V only; Nano R4 is 5 V logic.
- ESP32 → R4 UART: `Serial1.begin(9600, SERIAL_8N1, D9, D8)` on the ESP32 (TX = D8); R4 `Serial1` RX = D0. Always use D-labels.
- Board package for the ESP32: "Arduino ESP32 Boards" (by Arduino) **2.0.18-arduino.5** (core 2.x LEDC API: `ledcSetup`/`ledcAttachPin`). Mac must match.
- Wi-Fi (Stage 7): ESP32's **own open network "DFAB-ESP32"**, captive portal, page at http://192.168.4.1. No hotspot; `secrets.h` (hotspot credentials) is unused but still git-ignored — never print its values.
- Stepper pins on the R4 (user, resolved): **PUL+ = D7, DIR+ = D5, ENA+ = D3.**
- Speaker: as drawn in README §5 but **gate on ESP32 D3 (not D6)**, **no capacitor, R3 = 100 Ω (2–5 W)**, no flyback diode, 12 V. Pots on 3V3 (A0/A1/A2).

## Tooling
- Python: standalone Python 3 in VS Code, use a virtual environment (`.venv`). Allowed: numpy, scipy, soundfile, librosa.
- Arduino: the user compiles and uploads in Arduino IDE 2. Compile-check every sketch before handing it over with the IDE's bundled
  arduino-cli (path in README header; FQBNs `arduino:esp32:nano_nora`, `arduino:renesas_uno:nanor4`). Don't upload without asking.
- The user works on both macOS and Windows: give commands for both when they differ.

## Folder layout
```
README_Arduino_ESP32_R4_Bridge.md   project memory — start with §0 "Resume here" (update at the end of each stage)
CLAUDE.md                           this file
esp32_wifi_to_r4/                   ESP32 sketch (.ino) + sounds.h (generated) + melodies.h, secrets.h (both unused)
r4_message_received/                R4 sketch (stepper, needs AccelStepper)
pot_test/                           ESP32 pot wiring test
python/                             convert_sounds.py (Stage 5), send_command.py (empty), preview/ (generated)
sounds/                             Regular Songs/ + Hack Songs/ (git-ignored) + clips.csv (role column)
.venv/                              Python 3.13 venv (Windows PC)
```
Arduino IDE needs each .ino inside a folder with the same name.

## Next action
**Resume from README §0.** Stages 0–6 ✅. Stage 7 (own Wi-Fi + captive portal) **and the HACK button** (7 knob songs +
7 HACK songs, `role` column in `sounds/clips.csv`) are built, compiled and simulated — **hardware test outstanding**
(user deferred it; test list in README §0). Then Stage 8 (integration). Volume hardware options still open.
Re-run `python/convert_sounds.py` whenever clips change (`sounds.h` is generated).
Copyrighted songs: never transcribe from memory; only process user-provided files. Keep audio git-ignored.
AccelStepper compile check: unzip `%LOCALAPPDATA%/Arduino15/staging/libraries/AccelStepper-1.64.0.zip` into scratchpad, pass `--libraries`.
Python edit scripts: never write `\r\n` in heredoc replacements (gets turned into real line breaks) — use chr(92).
Open: Mac core version (must be 2.0.18-arduino.5). Wi-Fi-blocking issue solved in Stage 7.
