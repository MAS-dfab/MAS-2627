import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from G4_arduino import Arduino
a = Arduino("COM4"); a.send("stat"); import time; time.sleep(1); a.read_lines()

a.set_aspeed(0, 3.4); a.send("stat"); time.sleep(1); a.read_lines()
a.set_heater(220); a.wait_for_temperature(220)