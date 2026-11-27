"""
Stage 5 - sound converter (runs on the laptop, not on the Arduino).

Reads the clips listed in sounds/clips.csv, cuts each chorus, converts it to 8 kHz 8-bit
and writes esp32_wifi_to_r4/sounds.h for the ESP32 sketch.
Chosen mode (2026-11-26): TEMPO_STEPS = 1 = "varispeed": one copy per clip, the ESP32 plays it
faster/slower like a record (pitch moves with tempo). TEMPO_STEPS > 1 instead pre-computes tempo
variants with the pitch kept (needs much more flash).
Also writes WAV previews to python/preview/ so you can check the cuts by ear.

clips.csv columns (one row per clip):
    file      path inside sounds/, e.g. "Regular Songs/xyz.mp3" (.mp3 or .wav)
    name      short label (shown in the Serial Monitor / on the page)
    role      channel = chosen with the knob (row order = knob order)
              hack    = played by the HACK button (row order = play order)
    start     where the chorus starts: mm:ss (e.g. 0:43 or 1:02.5) or seconds (43.5)
    length_s  clip length in seconds (at tempo x1.00)

Run from the DFAB_Bridge folder:
    Windows:  .venv\\Scripts\\python python\\convert_sounds.py
    macOS:    .venv/bin/python python/convert_sounds.py
Re-run it every time a clip or a setting changes, then re-upload the ESP32 sketch.
"""

import argparse
import csv
import os
import re
import sys

import librosa
import numpy as np
import soundfile as sf
import scipy.signal as sg

# ---------------------------------------------------------------- settings
# Output sample rate on the ESP32 (8 kHz = telephone quality, 8 KB per second per variant)
SAMPLE_RATE = 8000
# Cutting and time-stretching happen at this higher rate, then the result is resampled down
WORK_SR = 22050
# Tempo variants: 1 = varispeed (only the original, x1.00; the ESP32 changes the playback speed).
# >1 = exponential steps from TEMPO_MIN to TEMPO_MAX with the pitch kept (librosa time-stretch).
# Keep TEMPO_MIN / TEMPO_MAX equal to the values in esp32_wifi_to_r4.ino.
TEMPO_MIN = 0.67
TEMPO_MAX = 1.5
TEMPO_STEPS = 1
# Short fade in/out so clips don't start or end with a click
FADE_MS = 20
# Loudness matching: every clip is scaled to the same loudness, then a soft limiter rounds
# off the peaks that would go past full scale (quiet parts pass unchanged).
# LOUDNESS = target level (RMS of the louder half of the clip, full scale = 1.0):
#   0.25 = clean, about as loud as plain peak normalisation
#   0.35 = matched, mild limiting (~1 % of samples rounded)
#   0.45 = loud, more limiting (~4 % rounded)
#   0.8  = louder, heavily limited (~17-24 % rounded)  <- user's choice 2026-11-27
#   >0.5 = little extra loudness, clearly more compressed/distorted (full scale is the ceiling)
LOUDNESS = 0.8
# Remove bass below this frequency (Hz) before matching: the small speaker can't play it, and
# it uses up swing that the audible part could use. 0 = off.
HIGHPASS_HZ = 150
# Flash space for sound data: app partition 3 145 728 B minus ~0.79 MB sketch minus a margin
FLASH_BUDGET_BYTES = 2_100_000

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(ROOT, "sounds")
DEFAULT_CSV = os.path.join(SOUNDS_DIR, "clips.csv")
OUT_H = os.path.join(ROOT, "esp32_wifi_to_r4", "sounds.h")
PREVIEW_DIR = os.path.join(ROOT, "python", "preview")


def tempo_factors():
    """TEMPO_STEPS factors from TEMPO_MIN to TEMPO_MAX with equal ratios between them."""
    if TEMPO_STEPS == 1:
        return [1.0]
    return [TEMPO_MIN * (TEMPO_MAX / TEMPO_MIN) ** (k / (TEMPO_STEPS - 1)) for k in range(TEMPO_STEPS)]


def parse_time(text):
    """'1:02.5' or '62.5' -> 62.5 seconds."""
    text = text.strip()
    if not text:
        raise ValueError("empty start time")
    if ":" in text:
        minutes, seconds = text.split(":")
        return int(minutes) * 60 + float(seconds)
    return float(text)


def read_clip_list(csv_path):
    clips = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row_no, row in enumerate(csv.DictReader(f), start=2):
            try:
                start = parse_time(row["start"])
            except ValueError:
                sys.exit(f"clips.csv line {row_no} ({row['name']}): fill in the start time (mm:ss)")
            role = (row.get("role") or "channel").strip().lower()
            if role not in ("channel", "hack"):
                sys.exit(f"clips.csv line {row_no} ({row['name']}): role must be 'channel' or 'hack'")
            clips.append({
                "file": row["file"].strip(),
                "name": row["name"].strip(),
                "role": role,
                "start": start,
                "length": float(row["length_s"]),
            })
    if not clips:
        sys.exit("clips.csv has no clips")
    return clips


def fade(y, sr):
    n = min(int(sr * FADE_MS / 1000), len(y) // 2)
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    y[:n] *= ramp
    y[len(y) - n:] *= ramp[::-1]
    return y


def loudness(y, sr):
    """Level of the louder half of the clip: RMS over 50 ms windows, the quieter half ignored,
    so a quiet intro or pause doesn't make a clip look softer than it sounds."""
    n = int(0.05 * sr)
    frames = y[:len(y) // n * n].reshape(-1, n)
    rms = np.sort(np.sqrt((frames ** 2).mean(axis=1)))
    loud = rms[len(rms) // 2:]
    return float(np.sqrt((loud ** 2).mean()))


def match_loudness(y, sr):
    """High-pass, scale to LOUDNESS, soft-limit. Returns (signal, percent of samples rounded)."""
    if HIGHPASS_HZ > 0:
        sos = sg.butter(2, HIGHPASS_HZ, "highpass", fs=sr, output="sos")
        y = sg.sosfilt(sos, y).astype(np.float32)
    level = loudness(y, sr)
    if level < 1e-6:
        return y, 0.0
    y = y * (LOUDNESS / level)
    rounded = float(np.mean(np.abs(y) > 0.8) * 100)   # samples in the limiter's rounding zone
    y = np.tanh(y)                                     # soft limiter: ~linear below 0.5, never past 1
    return y * 0.99, rounded


def to_uint8(y):
    """-1..+1 float -> 0..255, silence = 128 (= 50 % PWM duty on the ESP32)."""
    return np.clip(np.round(y * 127.5 + 128.0), 0, 255).astype(np.uint8)


def convert_clip(clip):
    path = os.path.join(SOUNDS_DIR, clip["file"])
    if not os.path.isfile(path):
        sys.exit(f"not found: {path}")
    y, _ = librosa.load(path, sr=WORK_SR, mono=True, offset=clip["start"], duration=clip["length"])
    got = len(y) / WORK_SR
    if got < clip["length"] - 0.05:
        sys.exit(f"{clip['name']}: only {got:.1f} s left after start {clip['start']:.1f} s "
                 f"(asked for {clip['length']:.1f} s) - start time too late?")
    variants = []
    stats = None
    for factor in tempo_factors():
        # rate > 1 = faster/shorter, pitch stays the same. x1.00 is left untouched
        # (time_stretch slightly smears the sound even at rate 1.0)
        stretched = y if factor == 1.0 else librosa.effects.time_stretch(y, rate=factor)
        low = librosa.resample(stretched, orig_sr=WORK_SR, target_sr=SAMPLE_RATE).astype(np.float32)
        # loudness compared with the old method (plain peak normalisation), for the report
        before = loudness(low / max(np.max(np.abs(low)), 1e-6) * 0.98, SAMPLE_RATE)
        low, rounded = match_loudness(low, SAMPLE_RATE)
        low = fade(low, SAMPLE_RATE)                   # fade last, so every clip ends at silence
        if stats is None:
            stats = (20 * np.log10(loudness(low, SAMPLE_RATE) / before), rounded)
        variants.append(to_uint8(low))
    return variants, stats


def c_name(index, step):
    return f"CLIP{index}_T{step}"


def write_header(clips, all_variants, factors, out_h):
    lines = [
        "// GENERATED by python/convert_sounds.py - do not edit by hand, re-run the script instead.",
        "// Contains audio from the user's own files: do not share or commit (see .gitignore).",
        "#pragma once",
        "#include <stdint.h>",
        "",
        f"#define SOUND_SAMPLE_RATE {SAMPLE_RATE}",
        f"#define SOUND_TEMPO_STEPS {TEMPO_STEPS}",
        "// tempo factor of each variant (index 0 = slowest)",
        "const float SOUND_TEMPOS[SOUND_TEMPO_STEPS] = {" + ", ".join(f"{f:.4f}f" for f in factors) + "};",
        "",
    ]
    for i, variants in enumerate(all_variants):
        for k, data in enumerate(variants):
            lines.append(f"// {clips[i]['name']}, tempo x{factors[k]:.2f}, {len(data)} samples")
            lines.append(f"const uint8_t {c_name(i, k)}[] = {{")
            for j in range(0, len(data), 32):
                lines.append("  " + ",".join(str(v) for v in data[j:j + 32]) + ",")
            lines.append("};")
    lines += [
        "",
        "struct SoundVariant { const uint8_t* data; uint32_t length; };",
        "struct SoundClip { const char* name; SoundVariant variants[SOUND_TEMPO_STEPS]; };",
        "",
    ]

    def table(c_array, role, comment):
        rows = [(i, v) for i, v in enumerate(all_variants) if clips[i]["role"] == role]
        out = [f"// {comment}"]
        if rows:
            out.append(f"const SoundClip {c_array}[] = {{")
            for i, variants in rows:
                name = clips[i]["name"].replace('"', "'")
                parts = ", ".join(f"{{{c_name(i, k)}, {len(v)}}}" for k, v in enumerate(variants))
                out.append(f'  {{"{name}", {{{parts}}}}},')
            out.append("};")
        return out, len(rows)

    knob, n_knob = table("SOUND_CLIPS", "channel", "knob channels, in the row order of sounds/clips.csv (role = channel)")
    hack, n_hack = table("HACK_CLIPS", "hack", "HACK button songs, in play order (role = hack)")
    lines += knob + [f"const int SOUND_CLIP_COUNT = {n_knob};", ""]
    lines += hack + [f"#define HACK_CLIP_COUNT {n_hack}", ""]
    os.makedirs(os.path.dirname(out_h), exist_ok=True)
    with open(out_h, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def write_previews(clips, all_variants, factors, preview_dir):
    os.makedirs(preview_dir, exist_ok=True)
    for i, variants in enumerate(all_variants):
        safe = re.sub(r"[^A-Za-z0-9]+", "_", clips[i]["name"]).strip("_")
        for k, data in enumerate(variants):
            path = os.path.join(preview_dir, f"{clips[i]['role']}_{i}_{safe}_x{factors[k]:.2f}.wav")
            sf.write(path, (data.astype(np.float32) - 128.0) / 128.0, SAMPLE_RATE, subtype="PCM_U8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=DEFAULT_CSV, help="clip list (default: sounds/clips.csv)")
    parser.add_argument("--report-only", action="store_true", help="only print the storage estimate")
    parser.add_argument("--out", default=OUT_H, help="header to write (default: esp32_wifi_to_r4/sounds.h)")
    parser.add_argument("--preview-dir", default=PREVIEW_DIR, help="folder for WAV previews")
    args = parser.parse_args()

    clips = read_clip_list(args.csv)
    if not any(c["role"] == "channel" for c in clips):
        sys.exit("clips.csv needs at least one clip with role = channel (the knob)")
    factors = tempo_factors()
    estimate = sum(round(c["length"] * SAMPLE_RATE / f) for c in clips for f in factors)
    print(f"loudness matching: LOUDNESS {LOUDNESS}, high-pass {HIGHPASS_HZ or 'off'} Hz "
          f"(dB = compared with plain peak normalisation)")
    print(f"{len(clips)} clips x {TEMPO_STEPS} tempo variants "
          f"({', '.join(f'x{f:.2f}' for f in factors)}) at {SAMPLE_RATE} Hz")
    print(f"estimated sound data: {estimate:,} bytes of {FLASH_BUDGET_BYTES:,} budget")
    if estimate > FLASH_BUDGET_BYTES:
        scale = FLASH_BUDGET_BYTES / estimate
        sys.exit(f"TOO BIG: shorten the clips (length_s) to about {scale * 100:.0f} % "
                 f"or use fewer TEMPO_STEPS. Nothing written.")
    if args.report_only:
        return

    all_variants = []
    for i, clip in enumerate(clips):
        variants, (gain_db, rounded) = convert_clip(clip)
        all_variants.append(variants)
        sizes = " / ".join(f"{len(v) / SAMPLE_RATE:.1f}" for v in variants)
        print(f"  {i:2d} {clip['role']:7s} {clip['name']:24s} start {clip['start']:6.1f} s  length {sizes} s  "
              f"louder by {gain_db:+5.1f} dB  peaks rounded {rounded:4.1f} %")

    total = sum(len(v) for vs in all_variants for v in vs)
    write_header(clips, all_variants, factors, args.out)
    write_previews(clips, all_variants, factors, args.preview_dir)
    print(f"sound data: {total:,} bytes ({total / FLASH_BUDGET_BYTES * 100:.0f} % of budget)")
    print(f"written: {args.out}")
    print(f"previews: {args.preview_dir}")


if __name__ == "__main__":
    main()
