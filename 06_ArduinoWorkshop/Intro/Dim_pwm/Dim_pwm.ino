// Built-in LED pin (supports PWM)
const int ledPin = LED_BUILTIN;

void setup() {
  // Initialize serial communication and wait up to 2.5 seconds for a connection
  Serial.begin(115200);
  for (auto startNow = millis() + 2500; !Serial && millis() < startNow; delay(500));
  
  // set analog write resolution
  analogWriteResolution(12);

  Serial.println("Dim LED Example with Nano R4");
  delay(1000);
}

void loop() {
  for (int i=0; i<360; i++){
    float sine_value = sin(2*i*PI / 360);
    int pwm_value = (int)((sine_value + 1)*(4095/2));

    analogWrite(ledPin, pwm_value);

    if (i % 30 == 0){
      Serial.print("- Angle: ");
      Serial.print(i);
      Serial.print("°, PWM Value: ");
      Serial.println(pwm_value);
    }

    delay(10);
  }

  Serial.println("Cycle complete");
  delay(1000);
}