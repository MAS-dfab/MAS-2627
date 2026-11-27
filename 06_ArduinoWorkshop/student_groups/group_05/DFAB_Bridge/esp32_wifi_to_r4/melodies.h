// Melodies for the ESP32 tone player (Stage 4). The knob (A0) picks one: 1 zone per melody.
//
// Each note = { frequency in Hz, length in 16th notes }
//   length: 1 = 16th, 2 = 8th, 3 = dotted 8th, 4 = quarter, 6 = dotted quarter,
//           8 = half, 12 = dotted half, 16 = whole
//   REST = silence for that length
// Each melody also has QUARTER_MS: how long one quarter-note slot lasts at tempo x1.00
//   (smaller = faster). The speed slider then scales this by x0.67 ... x1.5.
//
// To add or replace a melody: write a new NOTE array, then add one line to MELODIES[] at the bottom.
// The number of knob zones follows the number of entries automatically.
//
// Melodies 1-7 are public-domain tunes written out from memory: check them by ear.

#pragma once
#include <stdint.h>

// ---- Note frequencies (Hz), same values as the standard Arduino pitches.h ----
#define REST    0
#define NOTE_G3 196
#define NOTE_C4 262
#define NOTE_D4 294
#define NOTE_E4 330
#define NOTE_F4 349
#define NOTE_G4 392
#define NOTE_GS4 415
#define NOTE_A4 440
#define NOTE_B4 494
#define NOTE_C5 523
#define NOTE_D5 587
#define NOTE_DS5 622
#define NOTE_E5 659

struct Note {
  uint16_t freq;     // Hz, or REST
  uint8_t  len16;    // length in 16th notes
};

struct Melody {
  const char* name;
  const Note* notes;
  uint16_t    count;
  uint16_t    quarterMs;   // quarter-note slot at tempo x1.00
};

// 0: your phrase from sketch_nov26a ("Du bist gut ge-nug" cadence).
//    Same timing as your sketch: quarter slot = 1.3 x 250 ms = 325 ms.
const Note MEL_GUT_GENUG[] = {
  {NOTE_E4, 2}, {NOTE_G4, 2}, {NOTE_A4, 4}, {NOTE_G4, 2}, {NOTE_E4, 8}, {REST, 2},
  {NOTE_D4, 2}, {NOTE_E4, 2}, {NOTE_G4, 2}, {NOTE_A4, 4}, {NOTE_C5, 8}, {REST, 4},
};

// 1: Ode to Joy (Beethoven, 9th symphony), C major
const Note MEL_ODE_TO_JOY[] = {
  {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_F4, 4}, {NOTE_G4, 4},
  {NOTE_G4, 4}, {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_D4, 4},
  {NOTE_C4, 4}, {NOTE_C4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4},
  {NOTE_E4, 6}, {NOTE_D4, 2}, {NOTE_D4, 8},
  {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_F4, 4}, {NOTE_G4, 4},
  {NOTE_G4, 4}, {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_D4, 4},
  {NOTE_C4, 4}, {NOTE_C4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4},
  {NOTE_D4, 6}, {NOTE_C4, 2}, {NOTE_C4, 8},
};

// 2: Twinkle Twinkle Little Star (French folk tune), C major
const Note MEL_TWINKLE[] = {
  {NOTE_C4, 4}, {NOTE_C4, 4}, {NOTE_G4, 4}, {NOTE_G4, 4}, {NOTE_A4, 4}, {NOTE_A4, 4}, {NOTE_G4, 8},
  {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_C4, 8},
  {NOTE_G4, 4}, {NOTE_G4, 4}, {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_D4, 8},
  {NOTE_G4, 4}, {NOTE_G4, 4}, {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_D4, 8},
  {NOTE_C4, 4}, {NOTE_C4, 4}, {NOTE_G4, 4}, {NOTE_G4, 4}, {NOTE_A4, 4}, {NOTE_A4, 4}, {NOTE_G4, 8},
  {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_C4, 8},
};

// 3: Frère Jacques (French folk round), C major
const Note MEL_FRERE_JACQUES[] = {
  {NOTE_C4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4}, {NOTE_C4, 4},
  {NOTE_C4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4}, {NOTE_C4, 4},
  {NOTE_E4, 4}, {NOTE_F4, 4}, {NOTE_G4, 8},
  {NOTE_E4, 4}, {NOTE_F4, 4}, {NOTE_G4, 8},
  {NOTE_G4, 2}, {NOTE_A4, 2}, {NOTE_G4, 2}, {NOTE_F4, 2}, {NOTE_E4, 4}, {NOTE_C4, 4},
  {NOTE_G4, 2}, {NOTE_A4, 2}, {NOTE_G4, 2}, {NOTE_F4, 2}, {NOTE_E4, 4}, {NOTE_C4, 4},
  {NOTE_C4, 4}, {NOTE_G3, 4}, {NOTE_C4, 8},
  {NOTE_C4, 4}, {NOTE_G3, 4}, {NOTE_C4, 8},
};

// 4: Alle meine Entchen (German folk song), C major
const Note MEL_ENTCHEN[] = {
  {NOTE_C4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4}, {NOTE_F4, 4},
  {NOTE_G4, 8}, {NOTE_G4, 8},
  {NOTE_A4, 4}, {NOTE_A4, 4}, {NOTE_A4, 4}, {NOTE_A4, 4},
  {NOTE_G4, 16},
  {NOTE_A4, 4}, {NOTE_A4, 4}, {NOTE_A4, 4}, {NOTE_A4, 4},
  {NOTE_G4, 16},
  {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_F4, 4},
  {NOTE_E4, 8}, {NOTE_E4, 8},
  {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_D4, 4},
  {NOTE_C4, 16},
};

// 5: Für Elise (Beethoven), opening theme, A minor
const Note MEL_FUR_ELISE[] = {
  {NOTE_E5, 1}, {NOTE_DS5, 1},
  {NOTE_E5, 1}, {NOTE_DS5, 1}, {NOTE_E5, 1}, {NOTE_B4, 1}, {NOTE_D5, 1}, {NOTE_C5, 1},
  {NOTE_A4, 2}, {REST, 1}, {NOTE_C4, 1}, {NOTE_E4, 1}, {NOTE_A4, 1},
  {NOTE_B4, 2}, {REST, 1}, {NOTE_E4, 1}, {NOTE_GS4, 1}, {NOTE_B4, 1},
  {NOTE_C5, 2}, {REST, 1}, {NOTE_E4, 1}, {NOTE_E5, 1}, {NOTE_DS5, 1},
  {NOTE_E5, 1}, {NOTE_DS5, 1}, {NOTE_E5, 1}, {NOTE_B4, 1}, {NOTE_D5, 1}, {NOTE_C5, 1},
  {NOTE_A4, 2}, {REST, 1}, {NOTE_C4, 1}, {NOTE_E4, 1}, {NOTE_A4, 1},
  {NOTE_B4, 2}, {REST, 1}, {NOTE_E4, 1}, {NOTE_C5, 1}, {NOTE_B4, 1},
  {NOTE_A4, 4},
};

// 6: Mary Had a Little Lamb (American folk song), C major
const Note MEL_MARY[] = {
  {NOTE_E4, 4}, {NOTE_D4, 4}, {NOTE_C4, 4}, {NOTE_D4, 4},
  {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_E4, 8},
  {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_D4, 8},
  {NOTE_E4, 4}, {NOTE_G4, 4}, {NOTE_G4, 8},
  {NOTE_E4, 4}, {NOTE_D4, 4}, {NOTE_C4, 4}, {NOTE_D4, 4},
  {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4},
  {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4}, {NOTE_D4, 4},
  {NOTE_C4, 16},
};

// 7: Jingle Bells (J. Pierpont, 1857), chorus, C major
const Note MEL_JINGLE_BELLS[] = {
  {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_E4, 8},
  {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_E4, 8},
  {NOTE_E4, 4}, {NOTE_G4, 4}, {NOTE_C4, 6}, {NOTE_D4, 2},
  {NOTE_E4, 16},
  {NOTE_F4, 4}, {NOTE_F4, 4}, {NOTE_F4, 6}, {NOTE_F4, 2},
  {NOTE_F4, 4}, {NOTE_E4, 4}, {NOTE_E4, 4}, {NOTE_E4, 2}, {NOTE_E4, 2},
  {NOTE_E4, 4}, {NOTE_D4, 4}, {NOTE_D4, 4}, {NOTE_E4, 4},
  {NOTE_D4, 8}, {NOTE_G4, 8},
};

#define MELODY_ENTRY(name, arr, quarterMs) { name, arr, (uint16_t)(sizeof(arr) / sizeof(arr[0])), quarterMs }

// Knob zones, from knob fully left (0) to fully right (7)
const Melody MELODIES[] = {
  MELODY_ENTRY("Du bist gut genug",   MEL_GUT_GENUG,     325),
  MELODY_ENTRY("Ode to Joy",          MEL_ODE_TO_JOY,    450),
  MELODY_ENTRY("Twinkle Twinkle",     MEL_TWINKLE,       400),
  MELODY_ENTRY("Frere Jacques",       MEL_FRERE_JACQUES, 400),
  MELODY_ENTRY("Alle meine Entchen",  MEL_ENTCHEN,       350),
  MELODY_ENTRY("Fur Elise",           MEL_FUR_ELISE,     480),
  MELODY_ENTRY("Mary Had a Little Lamb", MEL_MARY,       400),
  MELODY_ENTRY("Jingle Bells",        MEL_JINGLE_BELLS,  320),
};
const int MELODY_COUNT = sizeof(MELODIES) / sizeof(MELODIES[0]);
