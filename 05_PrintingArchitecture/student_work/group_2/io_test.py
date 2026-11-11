import json
import os
import time

# IO test for the two extruder speeds. THE ROBOT DOES NOT MOVE: only the digital outputs change.
# Watch the extruder serial monitor while it runs and note what it prints at every step.
# The extruder WILL push material (about 20 s in total): keep the nozzle away from the print.
#
# DO1 on                 = extruder off
# DO2 on (DO1, DO3 off)  = aspeed 1 on this robot (IDE: aspeed 1 1 -> 1 mm/s)
# DO3 on (DO1, DO2 off)  = aspeed 0 on this robot (IDE: aspeed 0 7 -> 7 mm/s)

HERE = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(HERE, "config.json")

STATES = {
    "off": (True, False, False),
    "DO2 1mm/s": (False, True, False),    # DO2 -> aspeed 1
    "DO3 7mm/s": (False, False, True),    # DO3 -> aspeed 0
}

# (state, seconds). Test A switches DO2 -> DO3 directly, test B goes through "off" for 1 s in between.
STEPS = [
    ("off", 2),
    ("DO2 1mm/s", 4),
    ("DO3 7mm/s", 4),   # A: direct switch
    ("DO2 1mm/s", 4),
    ("off", 1),
    ("DO3 7mm/s", 4),   # B: from off
    ("off", 1),
]


def set_state(ur, urc, name):
    d1, d2, d3 = STATES[name]
    # outputs that switch off first, so DO2 and DO3 are never on together (that is retract)
    for pin, value in ((1, d1), (2, d2), (3, d3)):
        if not value:
            ur.send(urc.SetDigital(pin, False))
    for pin, value in ((1, d1), (2, d2), (3, d3)):
        if value:
            ur.send(urc.SetDigital(pin, True))


def main():
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    import compas_urc as urc

    ur = urc.URClient(config["robot_ip"])
    ur.connect()
    try:
        start = time.time()
        for name, seconds in STEPS:
            set_state(ur, urc, name)
            ur.send(urc.WaitTime(seconds))
            print(f"queued: {name:10s} for {seconds} s")
        print("watch the extruder serial monitor now")
        while True:
            try:
                ur.wait_all(timeout=0.5)   # short waits so Ctrl+C works on Windows
                break
            except urc.TimeoutException:
                pass
        print(f"done after {time.time() - start:.0f} s")
        ur.close()
    except (KeyboardInterrupt, Exception) as error:
        ur.abort({1: True, 2: False, 3: False})   # extruder off
        print("aborted:", error)


if __name__ == "__main__":
    main()
