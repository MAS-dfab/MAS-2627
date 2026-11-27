// Nano ESP32 — pot wiring test (no Wi-Fi, no smoothing, no deadband).
// Prints the RAW reading (0..4095) and the voltage (mV) on A0, A1, A2 twice a second.
// Open Tools -> Serial Monitor at 115200.
//
// Expected with pot VCC on 3V3, GND on GND:
//   pot at one end  -> about 0 / 0 mV
//   pot at the other end -> about 4095 / 3100+ mV
//   values change smoothly in between

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  delay(1500);   // time to open the Serial Monitor
  Serial.println("pot_test starting");
}

void printPot(const char* name, int pin) {
  Serial.print(name);
  Serial.print(" raw=");
  Serial.print(analogRead(pin));
  Serial.print(" mV=");
  Serial.print(analogReadMilliVolts(pin));
  Serial.print("   ");
}

void loop() {
  printPot("A0", A0);
  printPot("A1", A1);
  printPot("A2", A2);
  Serial.println();
  delay(500);   // fine here: this test sketch does nothing else
}
