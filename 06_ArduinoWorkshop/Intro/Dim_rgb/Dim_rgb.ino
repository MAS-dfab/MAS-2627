// Built-in RGB pin (supports PWM)
const int ledR = LEDR;
const int ledG = LEDG;
const int ledB = LEDB;

void setup() {
  // Initialize serial communication and wait up to 2.5 seconds for a connection
  Serial.begin(115200);
  for (auto startNow = millis() + 2500; !Serial && millis() < startNow; delay(500));
  
  // set analog write resolution
  analogWriteResolution(12);

  Serial.println("Dim RGB Example with Nano R4");
  delay(1000);
}

void loop() {

  for (int i=0; i<360; i++){
    float ar = sin(i * PI / 180);
    float ag = sin((i+90) * PI / 180);
    float ab = sin(i * PI / 180);
    int vr = (int)((1+ar) * 4095/2);
    int vg = (int)((1+ag+0.5) * 4095/2);
    int vb = (int)((1+ab) * 4095/2);

    analogWrite(ledR, vr);
    analogWrite(ledG, vg);
    analogWrite(ledB, vb);
    delay(50);

    Serial.println(String(vr) + "," + String(vg) + "," + String(vb));
  }

  Serial.println("Cycle complete");
  delay(1000);

}