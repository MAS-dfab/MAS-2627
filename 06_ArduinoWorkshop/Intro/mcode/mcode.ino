/*
  Standard Morse timing (all relative to one UNIT):
    dot            = 1 unit on
    dash           = 3 units on
    gap in letter  = 1 unit off
    gap in letters = 3 units off
    gap in words   = 7 units off
*/

const int LED_PIN = LED_BUILTIN;
const unsigned int UNIT = 200;   // ms per unit; lower = faster (e.g. 100)

// A–Z
const char* LETTERS[] = {
  ".-",   "-...", "-.-.", "-..",  ".",    "..-.", "--.",  "....", "..",
  ".---", "-.-",  ".-..", "--",   "-.",   "---",  ".--.", "--.-", ".-.",
  "...",  "-",    "..-",  "...-", ".--",  "-..-", "-.--", "--.."
};

// 0–9
const char* DIGITS[] = {
  "-----", ".----", "..---", "...--", "....-",
  ".....", "-....", "--...", "---..", "----."
};

// Returns the Morse string for a character, or nullptr if unsupported
const char* toMorse(char c) {
  c = toupper(c);
  if (c >= 'A' && c <= 'Z') return LETTERS[c - 'A'];
  if (c >= '0' && c <= '9') return DIGITS[c - '0'];
  return nullptr;
}

// Blink one character's dots and dashes
void playCode(const char* code) {
  for (int i = 0; code[i] != '\0'; i++) {
    digitalWrite(LED_PIN, HIGH);

    if (code[i] == '.') {
      delay(UNIT);
    } else {
      delay(UNIT * 3);
    }

    digitalWrite(LED_PIN, LOW);
    if (code[i + 1] != '\0'){
      delay(UNIT);   // gap between symbols
    } 
  }
}

// Blink a whole message
void playMessage(const String& msg) {
  for (unsigned int i = 0; i < msg.length(); i++) {
    char c = msg[i];

    if (c == ' ') {
      Serial.print("/ ");
      delay(UNIT * 4);   // 3 units already waited after last letter -> 7 total
      continue;
    }

    const char* code = toMorse(c);
    if (code == nullptr) {
      Serial.print("?");   // unsupported character, skipped
      continue;
    }

    Serial.print(code);
    Serial.print(' ');
    playCode(code);
    delay(UNIT * 3);         // gap between letters
  }
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(115200);
  while (!Serial) {
    delay(100);
  }
  Serial.println("Blinker ready.");
  Serial.println("Type a message and press Enter:");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() == 0) {
      return;
    }

    Serial.print("Text:  ");
    Serial.println(input);
    Serial.print("Morse: ");
    playMessage(input);
    Serial.println();
    Serial.println("Type a message and press Enter:");
  }
}