"""
Temple + base + domino, taken from the "Brick wall" Python component in
(video)brick_to_robot.ghx so the animation can import it.

temple_scene() returns the bricks grouped into build stages.
"""

from compas.geometry import Vector, cross_vectors
from compas.geometry import Frame

from brick_element import Brick


def create_temple_base(compas_crv, param, base_layers=2, base_row=3):
    base_bricks = []
    pt = compas_crv.point_at(param)
    temp_pt = pt.copy()
    temp_pt.z += Brick.HEIGHT / 2

    yv = compas_crv.tangent_at(param)
    yv.unitize()
    zv = Vector(0,0,1)
    xv = yv.cross(zv)

    d_x = (Brick.LENGTH + 1)/2

    if base_layers == 1:
        for sign in (1, -1):
            origin_pt = temp_pt + xv * (d_x * sign)
            base_bricks.append(Brick(Frame(origin_pt, xv, yv), "laying"))
    else:
        for i in range(base_layers):
            for j in range(base_row):
                if i % 2 == j % 2:
                    for sign in (1,-1):
                            if j == 0 and sign == -1:
                                continue
                            origin_pt = temp_pt + zv * i * Brick.HEIGHT + xv * d_x *j * sign
                            laying_frame = Frame(origin_pt, xv, yv)
                            brick = Brick(laying_frame, "laying")
                            base_bricks.append(brick)
    top_center_pt = pt + zv * base_layers * Brick.HEIGHT
    return base_bricks, top_center_pt


def create_temple(compas_crv, param, top_lapping, num_layers, starting_pt= None):
    temple_bricks =[]
    if starting_pt is None:
        starting_pt = compas_crv.point_at(param)
    yv = compas_crv.tangent_at(param)
    yv.unitize()
    zv = Vector(0,0,1)
    xv = yv.cross(zv)

    d_x = Brick.LENGTH / 2 - top_lapping +  Brick.HEIGHT /2
    d_z = Brick.LENGTH
    temp_pt = starting_pt.copy()
    temp_pt.z += d_z /2

    # center pt (origin) of standing bricks
    for i in range(num_layers):
        for sign in (1, -1):
            origin_s = temp_pt + zv * d_z * (i)
            origin_s += xv * d_x * sign
            standing_frame = Frame(origin_s, xv, yv)
            temple_bricks.append(Brick(standing_frame, "standing"))


    # center pt (origin) of laying brick (top brick)
    origin_l = temp_pt + zv * d_z * (num_layers-0.5) + zv * (Brick.HEIGHT/2)
    laying_frame = Frame(origin_l, xv, yv)
    temple_bricks.append(Brick(laying_frame, "laying"))
    return temple_bricks


def domino(compas_crv, gap, list_top=None, pick_number=None):
    domino_bricks = []
    length = Brick.WIDTH + gap
    crv_length = compas_crv.length()
    count = int(crv_length // length)

    params, points= compas_crv.divide_by_count(count, True)
    if pick_number is not None:
        for i, top in enumerate(list_top):
            points[pick_number + i] = top

    for param, pt in zip(params, points):
        tangent = compas_crv.tangent_at(param)
        origin = pt + Vector(0, 0, Brick.LENGTH / 2)
        frame = Frame(origin, xaxis = tangent, yaxis = cross_vectors(tangent, [0,0,1]))
        domino_bricks.append(Brick(frame, brick_type = "standing"))

    return domino_bricks


# ==========================================
# ONE TEMPLE + ITS BASE + NEIGHBOUR DOMINOS
# ==========================================

class Stages(list):
    """List of (title, bricks) that also carries the input parameters
    in .params (shown as annotations by temple_animation)."""
    params = {}

def temple_scene(compas_crv, gap, pick_number, lapping, layers, n_domino=6):
    """
    Returns (stages, tangent_at_temple)
    stages: list of (title, [Brick, ...]) in build order.
    n_domino: dominos kept on each side of pick_number.
    """

    length = Brick.WIDTH + gap
    count = int(compas_crv.length() // length)
    params, points = compas_crv.divide_by_count(count, True)

    pick_number = int(pick_number)
    if not 1 <= pick_number < len(params):
        raise ValueError("pick_number must be between 1 and %d" % (len(params) - 1))

    param = params[pick_number]

    base_bricks, top_base = create_temple_base(compas_crv, param, base_layers=2, base_row=3)
    prev_base, prev_pt = create_temple_base(compas_crv, params[pick_number - 1], base_layers=1, base_row=2)

    list_top = [prev_pt, top_base]
    domino_bricks = domino(compas_crv, gap, list_top, pick_number - 1)
    temple_bricks = create_temple(compas_crv, param, lapping, num_layers=layers, starting_pt=top_base)

    lo = max(0, pick_number - n_domino)
    hi = min(len(domino_bricks), pick_number + n_domino + 1)
    domino_bricks = domino_bricks[lo:hi]

    # ---- group into stages ----
    stages = Stages()
    stages.params = {
        "layers": layers, "lapping": lapping, "gap": gap,
        "pick_number": pick_number, "n_domino": n_domino,
        "crv_length": compas_crv.length(), "count": count,
        "ground_z": compas_crv.point_at(param).z,
    }

    base_z = sorted(set(round(b.frame.point.z, 3) for b in base_bricks))
    for n, z in enumerate(base_z):
        stages.append(("TEMPLE BASE  -  LAYER %d" % (n + 1),
                       [b for b in base_bricks if round(b.frame.point.z, 3) == z]))

    stages.append(("SIDE BASE", prev_base))
    stages.append(("DOMINO", domino_bricks))

    standing, top = temple_bricks[:-1], temple_bricks[-1]
    for n in range(0, len(standing), 2):
        stages.append(("STANDING PAIR  -  LAYER %d" % (n // 2 + 1), standing[n:n + 2]))
    stages.append(("TOP BRICK", [top]))

    tangent = compas_crv.tangent_at(param)
    tangent.unitize()

    return stages, tangent
