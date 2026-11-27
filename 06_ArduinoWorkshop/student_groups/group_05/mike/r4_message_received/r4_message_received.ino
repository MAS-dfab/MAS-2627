// Nano R4 — prints messages from the ESP32 and flashes its LED on each one,
// so you can see messages arrive even without the laptop connected.
//
// Wiring: ESP32 D8 -> R4 D0 (RX), ESP32 GND -> R4 GND

void setup() {
  Serial.begin(9600);     // USB: Serial Monitor (optional)
  Serial1.begin(9600);    // from the ESP32 on D0 (RX)
  pinMode(LEDR, OUTPUT);
  pinMode(LEDB, OUTPUT);
  pinMode(LEDG, OUTPUT);
  digitalWrite(LEDG, HIGH);
  digitalWrite(LEDB, HIGH);
  digitalWrite(LEDR, HIGH);
}

void loop() {
  if (Serial1.available()) {
    String message = Serial1.readStringUntil('\n');

    digitalWrite(LEDG, LOW);
    digitalWrite(LEDB, LOW);  // flash = a message arrived
    delay(1000);
    digitalWrite(LEDG, HIGH);
    digitalWrite(LEDB, HIGH);

    if (Serial) Serial.println("Nano R4 received: " + message);
  }
  if (!Serial1.available()){
    digitalWrite(LEDR, LOW);
    delay(1000);
    digitalWrite(LEDR, HIGH);
  }
}