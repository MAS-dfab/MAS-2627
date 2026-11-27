#!/usr/bin/env python3
"""
Type colours in the terminal and send them to the NeoPixel over MQTT.

    pip install paho-mqtt
    python neo_cli.py

Accepted input:
    255 0 0      or  255,0,0     RGB values
    #ff8800      or  ff8800      hex
    red / green / blue / white / yellow / cyan / purple / orange / pink
    off
    q            quit
"""
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "mike/neo/set"      # must match MQTT_TOPIC in the sketch

NAMES = {
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
    "white": (255, 255, 255), "yellow": (255, 200, 0), "cyan": (0, 255, 255),
    "purple": (160, 0, 255), "orange": (255, 100, 0), "pink": (255, 60, 150),
}


def parse(text: str):
    """Turn user input into the payload the sketch expects, or None if invalid."""
    t = text.strip().lower()
    if t == "off":
        return "off"
    if t in NAMES:
        return "{},{},{}".format(*NAMES[t])
    h = t.lstrip("#")
    if len(h) == 6 and all(c in "0123456789abcdef" for c in h):
        return "{},{},{}".format(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    parts = t.replace(",", " ").split()
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        vals = [int(p) for p in parts]
        if all(0 <= v <= 255 for v in vals):
            return "{},{},{}".format(*vals)
    return None


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    print(f"Connecting to {BROKER}...")
    client.connect(BROKER, PORT, keepalive=30)
    client.loop_start()
    print(f"Connected. Sending to '{TOPIC}'.")
    print("Type a colour: 255 0 0 | #ff8800 | red | off | q to quit\n")

    try:
        while True:
            text = input("colour> ")
            if text.strip().lower() in ("q", "quit", "exit"):
                break
            payload = parse(text)
            if payload is None:
                print("  ? not understood, try: 255 0 0, #ff8800, red, off")
                continue
            client.publish(TOPIC, payload).wait_for_publish()
            print("  sent", payload)
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        client.loop_stop()
        client.disconnect()
        print("Bye")


if __name__ == "__main__":
    main()