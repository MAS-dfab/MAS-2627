# region --- IMPORTS ---
import re
import time

import serial  # pip install pyserial

# endregion

# region --- ARDUINO ---
"""
Talk to the extruder Arduino (dbt-mini-shield firmware, Arduino Mega) over USB serial, with the same
commands you type in the Arduino IDE serial monitor (115200 baud, "New Line"):
    heater 1 220      -> heater ON (1) at 220 degrees      (heater 0 ... = off)
    aspeed 0 3        -> extrusion speed preset 0 (selected by robot DO 6) to 3   (0-20)
    aspeed 1 5        -> extrusion speed preset 1 (selected by robot DO 7) to 5   (0-20)
    stat              -> prints the status, with "TEMP : 199.57"

The Arduino IDE serial monitor must be CLOSED: only one program can use the port.
The Mega RESTARTS when the port is opened (and its firmware then switches the heater off), so:
    - the constructor waits for the restart before sending anything
    - set the heater AFTER opening the port, every time
    - after the print, closing the port does NOT restart it: the heater stays on.
      Opening the port again (also the serial monitor) restarts it and switches the heater off.
"""

TEMP_PATTERN = r"TEMP\s*:\s*([-\d.]+)"      # the temperature in the "stat" answer: "TEMP : 199.57"


class Arduino:
    def __init__(self, port="COM4", baudrate=115200, reset_wait=3.0, log=True):
        """port: the same port as in the Arduino IDE (bottom right of the window), e.g. "COM4"."""
        self.serial = serial.Serial(port, baudrate, timeout=0.1)
        self.log = log
        time.sleep(reset_wait)          # the Mega restarts when the port opens
        self.read_lines()               # drop the banner it prints while starting

    # ----- basic -----
    def send(self, command):
        """Send one line, e.g. "aspeed 0 3.4"."""
        self.serial.write((command.strip() + "\n").encode())
        self.serial.flush()
        if self.log:
            print(">>", command)

    def read_lines(self):
        """All complete lines the Arduino has sent since the last read (non-blocking)."""
        lines = []
        while self.serial.in_waiting:
            line = self.serial.readline().decode(errors="ignore").strip()
            if line:
                lines.append(line)
                if self.log:
                    print("<<", line)
        return lines

    def close(self):
        """Closing does not restart the Arduino: heater and presets stay as they are."""
        self.serial.close()

    # ----- extruder -----
    def set_heater(self, temperature, on=True):
        """heater 1 220 = on at 220 degrees, heater 0 ... = off."""
        self.send("heater {} {}".format(1 if on else 0, temperature))

    def set_aspeed(self, preset, value, decimals=2):
        """aspeed 0 3.40: preset 0 (robot DO 6) or 1 (robot DO 7), value 0-20."""
        value = max(0.0, min(20.0, float(value)))
        self.send("aspeed {} {:.{}f}".format(preset, value, decimals))

    def read_temperature(self, query="stat", pattern=TEMP_PATTERN, wait=1.0):
        """Ask once and return the temperature, or None if no answer within `wait` seconds."""
        regex = re.compile(pattern, re.IGNORECASE)
        self.send(query)
        end = time.time() + wait
        while time.time() < end:
            for line in self.read_lines():
                match = regex.search(line)
                if match:
                    return float(match.group(1))
            time.sleep(0.05)
        return None

    def wait_for_temperature(self, target, tolerance=3.0, stable_time=10.0, timeout=900.0,
                             query="stat", pattern=TEMP_PATTERN, every=1.0):
        """Ask the temperature every `every` seconds until it is within `tolerance` of `target`
        for `stable_time` seconds in a row. Prints the temperature every 10 s while waiting.
        Returns the last temperature read. Raises TimeoutError if it never gets there."""
        start = time.time()
        stable_since = None
        last = None
        next_print = 0.0
        log, self.log = self.log, False             # don't print every stat line
        try:
            while time.time() - start < timeout:
                temp = self.read_temperature(query, pattern, wait=every)
                if temp is not None:
                    last = temp
                if time.time() >= next_print and last is not None:
                    print("temperature: {:.1f} / {}".format(last, target))
                    next_print = time.time() + 10.0
                if last is not None and abs(last - target) <= tolerance:
                    stable_since = stable_since or time.time()
                    if time.time() - stable_since >= stable_time:
                        print("temperature reached: {:.1f}".format(last))
                        return last
                else:
                    stable_since = None
                time.sleep(max(0.0, every - 0.1))
        finally:
            self.log = log
        raise TimeoutError("temperature did not reach {} (last read: {})".format(target, last))

# endregion