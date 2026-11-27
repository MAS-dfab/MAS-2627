// Nano ESP32 — joins your phone hotspot and forwards text to the Nano R4.
//
// Two ways to send (both need the IP printed in the Serial Monitor at startup):
//   1. Browser: open http://<ESP32 IP>, type, press Send
//   2. Script:  UDP text to <ESP32 IP> port 4210 (set ESP32_IP in send_command.py)
//
// Hotspot must be 2.4 GHz:
//   iPhone  -> Personal Hotspot -> "Maximize Compatibility" ON
//   Android -> Hotspot settings -> band 2.4 GHz
//
// Wiring (one-way):
//   ESP32 D8 (TX) -> R4 D0 (RX)
//   ESP32 GND     -> R4 GND

#include <WiFi.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include <ESPmDNS.h>

// Status LED (the small yellow/orange LED_BUILTIN, D13) — check Wi-Fi without the laptop:
//   blinking = still joining the hotspot (often only 1–3 s, easy to miss)
//   solid on = connected, ready to receive (this is the normal state)
//   off      = Wi-Fi lost
const char*    HOSTNAME  = "dfab-esp32";            // page also at http://dfab-esp32.local
const char*    WIFI_SSID = SECRET_SSID;       // CHANGE: hotspot name, exact spelling
const char*    WIFI_PASS = SECRET_PASS;   // CHANGE: hotspot password
const uint16_t UDP_PORT  = 4210;

WebServer server(80);
WiFiUDP   udp;
char      packet[128];
String    lastSent = "(nothing yet)";

// Join the hotspot; restart and retry if it takes longer than 30 s
void connectWiFi() {
  WiFi.mode(WIFI_STA);              // station mode: join an existing network
  WiFi.setAutoReconnect(true);      // rejoin by itself if the hotspot drops briefly
  WiFi.disconnect();                // clear any half-finished connection from before
  delay(100);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  if (Serial) Serial.print("Connecting to hotspot");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));   // blink while joining
    delay(500);
    if (Serial) Serial.print(".");
    if (millis() - start > 30000) {
      if (Serial) Serial.println(" failed, restarting");
      ESP.restart();
    }
  }
  if (Serial) Serial.println(" connected");
  WiFi.setSleep(false);             // no Wi-Fi power saving: faster page loads and replies
  digitalWrite(LED_BUILTIN, HIGH);  // solid on = connected
  MDNS.begin(HOSTNAME);             // fixed name, so the changing IP doesn't matter
}

// Forward one line of text to the R4
void sendToR4(String msg) {
  msg.trim();
  if (msg.length() == 0) return;
  Serial1.println(msg);
  lastSent = msg;
  if (Serial) {
    Serial.print("-> R4: ");
    Serial.println(msg);
  }
}

// Make text safe to show inside the web page
String htmlEscape(String s) {
  s.replace("&", "&amp;");
  s.replace("<", "&lt;");
  s.replace(">", "&gt;");
  return s;
}

void handleRoot() {
  if (Serial) {
    Serial.print("page request from ");
    Serial.println(server.client().remoteIP());
  }
  String html =
    "<!DOCTYPE html><html><head>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32 to R4</title></head>"
    "<body style='font-family:sans-serif;margin:24px'>"
    "<h2>Send to Nano R4</h2>"
    "<form action='/send' method='get'>"
    "<input name='msg' autofocus autocomplete='off' style='font-size:18px;width:70%'> "
    "<button style='font-size:18px'>Send</button>"
    "</form>"
    "<p>Last sent: " + htmlEscape(lastSent) + "</p>"
    "</body></html>";
  server.send(200, "text/html", html);
}

void handleSend() {
  if (server.hasArg("msg")) sendToR4(server.arg("msg"));
  server.sendHeader("Location", "/");
  server.send(303);
}

void setup() {
  // Very first thing: 3 quick flashes = this sketch version is running
  pinMode(LED_BUILTIN, OUTPUT);
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_BUILTIN, HIGH); delay(150);
    digitalWrite(LED_BUILTIN, LOW);  delay(150);
  }

  Serial.begin(115200);                      // USB: debug only
  Serial1.begin(9600, SERIAL_8N1, D9, D8);   // RX = D9 (GPIO18), TX = D8 (GPIO17)
  delay(1500);                               // time to open the Serial Monitor
  if (Serial) Serial.println("esp32_hotspot_to_r4 starting (LED version)");

  connectWiFi();

  server.on("/", handleRoot);
  server.on("/send", handleSend);
  server.begin();
  udp.begin(UDP_PORT);

  if (Serial) {
    Serial.print("Open http://");
    Serial.print(WiFi.localIP());            // address given by the phone (can change)
    Serial.print("  or http://");
    Serial.print(HOSTNAME);
    Serial.println(".local");
  }
}

void loop() {
  // LED off = Wi-Fi lost (the ESP32 keeps trying to rejoin by itself)
  digitalWrite(LED_BUILTIN, WiFi.status() == WL_CONNECTED ? HIGH : LOW);

  server.handleClient();

  int len = udp.parsePacket();
  if (len > 0) {
    int n = udp.read(packet, sizeof(packet) - 1);
    if (n < 0) n = 0;
    packet[n] = '\0';
    sendToR4(String(packet));
  }
}