#include <Adafruit_NeoPixel.h>

const int LED_PIN   = D6;   // pin name, not a bare number
const int LED_COUNT = 1;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  strip.begin();
  strip.setBrightness(50);
  strip.clear();
  strip.show();
}

void loop() {
  strip.setPixelColor(0, strip.Color(40, 160, 225));  // soft white
  strip.show();                                        // actually send it
  delay(500);
  strip.setPixelColor(0, strip.Color(225, 40, 160));  // soft white
  strip.show();                                        // actually send it
  delay(500);
  strip.setPixelColor(0, strip.Color(160, 225, 40));  // soft white
  strip.show();                                        // actually send it
  delay(500);
}