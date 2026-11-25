#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

const char* WIFI_SSID  = "a";
const char* WIFI_PASS  = "12345678";
const char* MQTT_HOST  = "broker.emqx.io";
const int   MQTT_PORT  = 1883;
const char* MQTT_TOPIC = "ananya/neo/set";          // (1) semicolon

const int LED_PIN   = 6;                           // (2) pin name, not 6
const int LED_COUNT = 1;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
WiFiClient net;
PubSubClient mqtt(net);

void setColor(int r, int g, int b) {
  strip.setPixelColor(0, strip.Color(r, g, b));
  strip.show();
  Serial.printf("colour -> %d,%d,%d\n", r, g, b);   // (4) no state publish
} 

void onMessage(char* topic, byte* payload, unsigned int length) {
  String text;
  for (unsigned int i = 0; i < length; i++) text += (char)payload[i];
  text.trim();

  if (text == "off") { setColor(0, 0, 0); return; }

  int r, g, b;
  if (sscanf(text.c_str(), "%d,%d,%d", &r, &g, &b) == 3) {
    setColor(constrain(r, 0, 255), constrain(g, 0, 255), constrain(b, 0, 255));
  } else {
    Serial.print("ignored: "); Serial.println(text);
  }
}

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.print(" OK, IP "); Serial.println(WiFi.localIP());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("MQTT...");
    String id = "nano-esp32-" + String((uint32_t)ESP.getEfuseMac(), HEX);  // (5) unique ID
    if (mqtt.connect(id.c_str())) {
      Serial.println(" OK");
      mqtt.subscribe(MQTT_TOPIC);                                          // (3) your topic
    } else {
      Serial.print(" failed, rc="); Serial.println(mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  strip.begin();
  strip.setBrightness(50);
  strip.clear();
  strip.show();

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
}