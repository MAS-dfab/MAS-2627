// Nano R4 — receives slider values from the ESP32 and drives the stepper (Stage 3).
//
// Wiring:
//   ESP32 D8 -> R4 D0 (RX), ESP32 GND -> R4 GND
//   R4 D7 -> driver PUL+    R4 D5 -> driver DIR+    R4 D3 -> driver ENA+
//   driver PUL-, DIR-, ENA- -> R4 GND      driver power: separate 12 V supply
//
// The ESP32 sends lines like "S1234 W2048" (both 0..4095), on change and every 500 ms:
//   S = speed slider (ESP32 A1) -> motor speed
//   W = detune slider (ESP32 A2) -> dwell = how long the motor runs before it reverses
// Any other line (text from the web page) is printed as text.
//
// Motion: run at full speed for the dwell time -> ramp down -> reverse -> ramp up -> ...
//   (no pause; the ramp passes smoothly through zero speed).
// Stops (ramps down) when the speed slider is below SPEED_STOP_THRESHOLD
// or when no slider message arrived for FAILSAFE_TIMEOUT_MS (failsafe).
// After IDLE_DISABLE_MS standing still, the driver is switched off via ENA (no heat).
//
// RGB LED (active LOW):  green = link OK   red = no slider message (failsafe)
//                        blue flash = a text message arrived
// Serial Monitor / Plotter: 115200, status line 4x per second.
//   The status line is skipped (never waits) when the USB buffer is full, so printing
//   cannot hold up the motor. maxgap_us = longest pause of loop() since the last line.
//
// No delay() and no readStringUntil(): runSpeed() must be called thousands of times per second.

#include <AccelStepper.h>

// =====================================================================
// Stepper settings: placeholders, replace the values after testing
// =====================================================================
// R4 pin -> driver PUL+
const int STEP_PIN = 7;
// R4 pin -> driver DIR+
const int DIR_PIN = 5;
// R4 pin -> driver ENA+
const int ENABLE_PIN = 3;
// true on most TB6600 drivers: ENA+ HIGH = motor OFF. Flip if the motor never turns.
const bool ENA_DISABLES_WHEN_HIGH = true;
// must match the driver DIP switches (1/8 microstep = 1600)
const long STEPS_PER_REV = 1600;
// speed just above the stop threshold, in steps per second
const float SPEED_MIN_STEPS_S = 0;
// speed with the speed slider at the top (4800 = 3 rev/s at 1/8 microstep = 1600 steps/rev)
const float SPEED_MAX_STEPS_S = 4800;
// speed slider values (0..4095) below this = motor stops
const int SPEED_STOP_THRESHOLD = 100;
// run time before reversing, with the detune slider at the bottom / top
const unsigned long DWELL_MIN_MS = 500;
const unsigned long DWELL_MAX_MS = 10000;
// acceleration for speeding up, slowing down and reversing (steps per second^2)
// = SPEED_MAX_STEPS_S -> 1 s from 0 to full speed, 2 s for a full reversal
const float RAMP_STEPS_S2 = 4800;
// step pulse length for the TB6600 (microseconds)
const int MIN_PULSE_US = 5;
// stop if no slider message from the ESP32 for this long
const unsigned long FAILSAFE_TIMEOUT_MS = 2000;
// switch the driver off after standing still this long
const unsigned long IDLE_DISABLE_MS = 3000;
// flip if the motor turns the "wrong" way first
const bool INVERT_DIRECTION = false;

// =====================================================================
// Other settings
// =====================================================================
// how often to print the status line
const unsigned long STATUS_INTERVAL_MS = 250;
// blue flash length for text messages
const unsigned long TEXT_FLASH_MS = 300;
// false = no status lines on USB
const bool PRINT_STATUS = true;

// ---- Values from the ESP32 (0..4095) ----
int speedRaw = 0;
int dwellRaw = 0;

// ---- Link state ----
// millis() of the last valid S/W line
unsigned long lastSliderMsg = 0;
// false until the first valid S/W line
bool everReceived = false;
// to print "link lost/restored" only once
bool linkWasOk = false;
// garbled or too long lines (should stay 0)
unsigned long badLines = 0;
// bytes received on D0, valid or not (wiring check)
unsigned long rxBytes = 0;

// ---- Line reader ----
char lineBuf[64];
int  lineLen = 0;
bool lineTooLong = false;

// ---- LEDs / printing ----
unsigned long lastStatus = 0;
unsigned long textFlashStart = 0;
bool textFlashOn = false;

// ---- Motion state ----
AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);
// signed speeds in steps per second (+ = one way, - = the other way)
float currentSpeed = 0;
float targetSpeed  = 0;
// +1 or -1, flips after every dwell
int direction = 1;
// true once the motor reached the target speed; the dwell timer then runs
bool atSpeed = false;
unsigned long dwellStart = 0;
unsigned long dwellMs = DWELL_MIN_MS;
bool driverEnabled = false;
unsigned long movingLastAt = 0;
unsigned long lastRampUs = 0;

// ---- Loop timing check ----
unsigned long lastLoopUs = 0;
// longest time between two loop() runs since the last status line (step timing check)
unsigned long maxGapUs = 0;

// =====================================================================
// Receiving (same as Stage 2)
// =====================================================================

// Read one number from text. Returns false if there is no number at p.
bool readNumber(const char* p, long& value, const char*& end) {
  char* e;
  value = strtol(p, &e, 10);
  end = e;
  return e != p;
}

// "S1234 W2048" -> speed = 1234, dwell = 2048. Returns false if the line is malformed.
bool parseSliderLine(const char* line, int& speed, int& dwell) {
  long s, w;
  const char* p;
  if (line[0] != 'S') return false;
  if (!readNumber(line + 1, s, p)) return false;
  if (p[0] != ' ' || p[1] != 'W') return false;
  if (!readNumber(p + 2, w, p)) return false;
  // nothing may follow
  if (*p != '\0') return false;
  if (s < 0 || s > 4095 || w < 0 || w > 4095) return false;
  speed = (int)s;
  dwell = (int)w;
  return true;
}

void handleLine(const char* line) {
  if (line[0] == '\0') return;

  // Slider line = starts with 'S' followed by a digit
  if (line[0] == 'S' && isdigit((unsigned char)line[1])) {
    int s, w;
    if (parseSliderLine(line, s, w)) {
      speedRaw = s;
      dwellRaw = w;
      lastSliderMsg = millis();
      everReceived = true;
    } else {
      badLines++;
      if (Serial) { Serial.print("bad line: "); Serial.println(line); }
    }
    return;
  }

  // Anything else: text from the web page / UDP
  if (Serial) { Serial.print("text: "); Serial.println(line); }
  digitalWrite(LEDB, LOW);
  textFlashStart = millis();
  textFlashOn = true;
}

// Collect characters from the ESP32; call handleLine() for every complete line.
void readSerial1() {
  while (Serial1.available()) {
    char c = Serial1.read();
    rxBytes++;
    // println sends \r\n: ignore the \r
    if (c == '\r') continue;
    if (c == '\n') {
      if (lineTooLong) badLines++;
      else { lineBuf[lineLen] = '\0'; handleLine(lineBuf); }
      lineLen = 0;
      lineTooLong = false;
    } else if (lineLen < (int)sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    } else {
      // drop the rest of this line
      lineTooLong = true;
    }
  }
}

bool linkOk() {
  return everReceived && (millis() - lastSliderMsg < FAILSAFE_TIMEOUT_MS);
}

// =====================================================================
// Motion (Stage 3)
// =====================================================================

void setDriverEnabled(bool on) {
  bool pinHigh = ENA_DISABLES_WHEN_HIGH ? !on : on;
  digitalWrite(ENABLE_PIN, pinHigh ? HIGH : LOW);
  driverEnabled = on;
}

// Speed slider (0..4095) -> speed in steps per second (always >= 0)
float speedFromSlider(int raw) {
  if (raw < SPEED_STOP_THRESHOLD) return 0;
  float t = (raw - SPEED_STOP_THRESHOLD) / (float)(4095 - SPEED_STOP_THRESHOLD);
  return SPEED_MIN_STEPS_S + t * (SPEED_MAX_STEPS_S - SPEED_MIN_STEPS_S);
}

// Detune slider (0..4095) -> dwell time in ms
unsigned long dwellFromSlider(int raw) {
  return DWELL_MIN_MS + (DWELL_MAX_MS - DWELL_MIN_MS) * (unsigned long)raw / 4095;
}

void updateMotion(bool link) {
  unsigned long now = millis();

  // Failsafe: without a link the target speed is 0 (the motor ramps down)
  float speedMagnitude = link ? speedFromSlider(speedRaw) : 0;
  dwellMs = dwellFromSlider(dwellRaw);

  // After running the dwell time at full speed: reverse.
  // The ramp below then slows down, passes through 0 and speeds up the other way.
  // While stopped (target 0) the dwell timer is reset: after a stop the motor keeps its
  // direction and runs a full dwell before the next reversal.
  if (speedMagnitude == 0) atSpeed = false;
  if (atSpeed && now - dwellStart >= dwellMs) {
    direction = -direction;
    atSpeed = false;
  }
  targetSpeed = direction * speedMagnitude;

  // Ramp: move currentSpeed toward targetSpeed by at most RAMP_STEPS_S2 per second, every 1 ms
  unsigned long nowUs = micros();
  unsigned long dtUs = nowUs - lastRampUs;
  if (dtUs >= 1000) {
    lastRampUs = nowUs;
    // cap, so a slow loop (e.g. USB printing) never causes a speed jump
    if (dtUs > 5000) dtUs = 5000;
    float maxChange = RAMP_STEPS_S2 * dtUs * 1e-6f;
    float diff = targetSpeed - currentSpeed;
    if (fabs(diff) <= maxChange) currentSpeed = targetSpeed;
    else currentSpeed += (diff > 0) ? maxChange : -maxChange;
    stepper.setSpeed(currentSpeed);
  }

  // Start the dwell timer once the (non-zero) target speed is reached
  if (!atSpeed && speedMagnitude > 0 && currentSpeed == targetSpeed) {
    atSpeed = true;
    dwellStart = now;
  }

  // ENA: on while moving (or about to move), off after IDLE_DISABLE_MS standing still
  if (targetSpeed != 0 || currentSpeed != 0) {
    if (!driverEnabled) setDriverEnabled(true);
    movingLastAt = now;
  } else if (driverEnabled && now - movingLastAt >= IDLE_DISABLE_MS) {
    setDriverEnabled(false);
  }

  // Makes a step when one is due (call as often as possible)
  stepper.runSpeed();
}

// =====================================================================

void setup() {
  Serial.begin(115200);
  Serial1.begin(9600);

  pinMode(LEDR, OUTPUT);
  pinMode(LEDG, OUTPUT);
  pinMode(LEDB, OUTPUT);
  // red until the first slider message
  digitalWrite(LEDR, LOW);
  digitalWrite(LEDG, HIGH);
  digitalWrite(LEDB, HIGH);

  pinMode(ENABLE_PIN, OUTPUT);
  // start with the driver off: it switches on when the motor should move
  setDriverEnabled(false);

  stepper.setMaxSpeed(SPEED_MAX_STEPS_S);
  stepper.setMinPulseWidth(MIN_PULSE_US);
  stepper.setPinsInverted(INVERT_DIRECTION, false, false);
  stepper.setSpeed(0);
}

// One status line, sent in one piece. Skipped if the USB buffer has no room:
// Serial.print() would otherwise wait for the PC, and the motor would stutter.
void printStatus(bool ok) {
  if (!Serial) return;
  char line[160];
  int len = snprintf(line, sizeof(line),
    "speed:%d dwell:%d target_s:%d steps_s:%d dwell_ms:%lu en:%d link:%d bad:%lu rx:%lu maxgap_us:%lu\r\n",
    speedRaw, dwellRaw, (int)targetSpeed, (int)currentSpeed, dwellMs,
    driverEnabled ? 1 : 0, ok ? 1 : 0, badLines, rxBytes, maxGapUs);
  if (len <= 0 || len >= (int)sizeof(line)) return;
  if (Serial.availableForWrite() < len) return;
  Serial.write((const uint8_t*)line, len);
  // start measuring again (the time spent printing shows up in the next line)
  maxGapUs = 0;
}

void loop() {
  // Measure the longest pause between loop() runs. At 4800 steps/s a step is due every 208 us,
  // so maxgap_us should stay well below that.
  unsigned long loopUs = micros();
  if (loopUs - lastLoopUs > maxGapUs) maxGapUs = loopUs - lastLoopUs;
  lastLoopUs = loopUs;

  readSerial1();

  bool ok = linkOk();
  // LEDs + message only when the link state changes
  if (ok != linkWasOk) {
    digitalWrite(LEDG, ok ? LOW : HIGH);
    digitalWrite(LEDR, ok ? HIGH : LOW);
    if (Serial) Serial.println(ok ? "link OK" : "LINK LOST (failsafe: motor ramps down)");
    linkWasOk = ok;
  }

  updateMotion(ok);

  // End the blue text flash without delay()
  if (textFlashOn && millis() - textFlashStart >= TEXT_FLASH_MS) {
    digitalWrite(LEDB, HIGH);
    textFlashOn = false;
  }

  if (PRINT_STATUS && millis() - lastStatus >= STATUS_INTERVAL_MS) {
    lastStatus = millis();
    printStatus(ok);
  }
}
