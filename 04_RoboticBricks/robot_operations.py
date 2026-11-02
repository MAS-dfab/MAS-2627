
from compas.geometry import Frame
import simple_ur_script as ur

SAFE_DIST = 50
BLEND_RAD = 10

HOME_JOINTS = [
    -2.13, -1.73, 1.84,
    -1.75, -1.63, 0.06
]


def pickup_brick(script, pick_frame, acceleration, velocity, IO):

    frames = []

    safe_frame = pick_frame.translated(
        pick_frame.zaxis * SAFE_DIST
    )

    script += ur.move_j(HOME_JOINTS, acceleration, velocity)

    script += ur.move_l(safe_frame, acceleration, velocity)
    frames.append(safe_frame)

    script += ur.move_l(pick_frame, acceleration, velocity)
    frames.append(pick_frame)

    script += ur.set_digital_out(IO, signal=True)
    script += ur.sleep(2)

    script += ur.move_l(safe_frame, acceleration, velocity)
    frames.append(safe_frame)

    script += ur.move_j(HOME_JOINTS, acceleration, velocity)

    return script, frames


def place_brick(script, place_frame, acceleration, velocity, IO):

    frames = []

    safe_frame = place_frame.translated(
        place_frame.zaxis * SAFE_DIST
    )

    script += ur.move_l(safe_frame, acceleration, velocity)
    frames.append(safe_frame)

    script += ur.move_l(
        place_frame,
        acceleration / 4,
        velocity / 4
    )
    frames.append(place_frame)

    script += ur.sleep(1)
    script += ur.set_digital_out(IO, signal=False)

    script += ur.move_l(
        safe_frame,
        acceleration / 4,
        velocity / 4
    )
    frames.append(safe_frame)

    return script, frames
