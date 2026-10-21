
import math

import Rhino.Geometry as rg

from compas.geometry import Point, Frame, Box


# ==========================================
# 1. DIMENSIONS (mm)
# ==========================================

BRICK_LENGTH = 32.0
BRICK_WIDTH = 15.0
BRICK_HEIGHT = 10.0

DOMINO_HEIGHT = 32.0
DOMINO_WIDTH = 15.0
DOMINO_THICKNESS = 10.0

EDGE_MARGIN = 0.5
TOLERANCE = 0.25


# ==========================================
# 2. CURVE HELPERS
# ==========================================

def curve_data(crv, distance):

    distance = max(
        0.0,
        min(float(distance), crv.GetLength())
    )

    success, t = crv.LengthParameter(distance)

    if not success:
        raise ValueError("Invalid curve distance")

    pt = crv.PointAt(t)
    tangent = crv.TangentAt(t)

    length = math.sqrt(
        tangent.X ** 2 + tangent.Y ** 2
    )

    if length < 0.000001:
        raise ValueError("Invalid curve tangent")

    return (
        pt.X,
        pt.Y,
        tangent.X / length,
        tangent.Y / length
    )


def distance_on_curve(crv, x, y):

    success, t = crv.ClosestPoint(
        rg.Point3d(x, y, 0)
    )

    if not success:
        return None

    if t <= crv.Domain.T0:
        return 0.0

    if t >= crv.Domain.T1:
        return crv.GetLength()

    interval = rg.Interval(
        crv.Domain.T0, t
    )

    return crv.GetLength(interval)


# ==========================================
# 3. SUPPORT HEIGHT
# ==========================================

def point_in_support(x, y, box):

    f = box.frame

    dx = x - f.point.x
    dy = y - f.point.y

    local_x = (
        dx * f.xaxis.x +
        dy * f.xaxis.y
    )

    local_y = (
        dx * f.yaxis.x +
        dy * f.yaxis.y
    )

    return (
        abs(local_x) <= box.xsize / 2.0 + TOLERANCE
        and
        abs(local_y) <= box.ysize / 2.0 + TOLERANCE
    )


def top_height(x, y, supports):

    height = 0.0

    for box in supports:

        if point_in_support(x, y, box):

            z = (
                box.frame.point.z +
                box.zsize / 2.0
            )

            height = max(height, z)

    return height


def height_at_distance(crv, distance, supports):

    x, y, _, _ = curve_data(crv, distance)

    return top_height(x, y, supports)


# ==========================================
# 4. FOOTPRINT VALIDATION
# ==========================================

def valid_footprint(
    x, y, z, tx, ty, supports
):

    # Sample footprint corners and center.
    # Domino thickness is along tangent.
    # Domino width is perpendicular.

    samples = [
        (0.0, 0.0),
        (-DOMINO_THICKNESS / 2.0, -DOMINO_WIDTH / 2.0),
        (-DOMINO_THICKNESS / 2.0,  DOMINO_WIDTH / 2.0),
        ( DOMINO_THICKNESS / 2.0, -DOMINO_WIDTH / 2.0),
        ( DOMINO_THICKNESS / 2.0,  DOMINO_WIDTH / 2.0),
        (-DOMINO_THICKNESS / 2.0, 0.0),
        ( DOMINO_THICKNESS / 2.0, 0.0)
    ]

    for along, across in samples:

        px = x + along * tx - across * ty
        py = y + along * ty + across * tx

        surface_z = top_height(
            px, py, supports
        )

        if abs(surface_z - z) > TOLERANCE:
            return False

    return True


# ==========================================
# 5. DOMINO GEOMETRY
# ==========================================

def make_domino(x, y, support_z, tx, ty):

    frame = Frame(
        Point(
            x,
            y,
            support_z + DOMINO_HEIGHT / 2.0
        ),
        [0, 0, 1],
        [-ty, tx, 0]
    )

    box = Box(
        DOMINO_HEIGHT,
        DOMINO_WIDTH,
        DOMINO_THICKNESS
    )

    box.frame = frame

    return box, frame


# ==========================================
# 6. BRICK EDGE CALCULATION
# ==========================================

def brick_edge_candidate(
    crv,
    box,
    edge_sign,
    supports,
    margin
):

    f = box.frame

    tx = f.xaxis.x
    ty = f.xaxis.y

    length = math.sqrt(tx * tx + ty * ty)

    if length < 0.000001:
        return None

    tx /= length
    ty /= length

    # Center-to-edge offset
    offset = (
        box.xsize / 2.0
        - DOMINO_THICKNESS / 2.0
        - margin
    )

    if offset < 0:
        return None

    x = f.point.x + edge_sign * offset * tx
    y = f.point.y + edge_sign * offset * ty

    z = f.point.z + box.zsize / 2.0

    # Test the footprint on the real top surface.
    if not valid_footprint(
        x, y, z, tx, ty, supports
    ):
        return None

    distance = distance_on_curve(crv, x, y)

    if distance is None:
        return None

    return {
        "s": distance,
        "x": x,
        "y": y,
        "z": z,
        "tx": tx,
        "ty": ty
    }


# ==========================================
# 7. SUPPORT CLASSIFICATION
# ==========================================

def classify_support(
    crv,
    box,
    supports,
    probe
):

    f = box.frame

    center_s = distance_on_curve(
        crv,
        f.point.x,
        f.point.y
    )

    if center_s is None:
        return "flat"

    current_z = (
        f.point.z + box.zsize / 2.0
    )

    before_z = height_at_distance(
        crv,
        center_s - probe,
        supports
    )

    after_z = height_at_distance(
        crv,
        center_s + probe,
        supports
    )

    if (
        current_z > before_z + TOLERANCE
        and current_z > after_z + TOLERANCE
    ):
        return "peak"

    if after_z > before_z + TOLERANCE:
        return "uphill"

    if before_z > after_z + TOLERANCE:
        return "downhill"

    return "flat"


# ==========================================
# 8. MAIN GENERATOR
# ==========================================

def generate_dominoes(
    crv,
    slope_bricks,
    floor_spacing=17.0,
    min_spacing=11.0,
    edge_margin=EDGE_MARGIN
):

    if crv is None:
        raise ValueError("Curve is missing")

    if floor_spacing < DOMINO_THICKNESS:
        raise ValueError(
            "Floor spacing must be >= 10 mm"
        )

    if min_spacing < DOMINO_THICKNESS:
        raise ValueError(
            "Minimum spacing must be >= 10 mm"
        )

    if edge_margin < 0:
        raise ValueError(
            "Edge margin cannot be negative"
        )

    supports = list(slope_bricks or [])

    warnings = []
    candidates = []

    curve_length = crv.GetLength()

    # ======================================
    # 9. EXPOSED EDGE CANDIDATES
    # ======================================

    support_records = []

    for box in supports:

        f = box.frame

        center_s = distance_on_curve(
            crv,
            f.point.x,
            f.point.y
        )

        if center_s is None:
            continue

        start = brick_edge_candidate(
            crv, box, -1,
            supports, edge_margin
        )

        end = brick_edge_candidate(
            crv, box, 1,
            supports, edge_margin
        )

        if start is None and end is None:
            continue

        z = f.point.z + box.zsize / 2.0

        support_records.append({
            "s": center_s,
            "z": z,
            "start": start,
            "end": end,
            "box": box
        })

    support_records.sort(
        key=lambda r: r["s"]
    )

    # ======================================
    # 10. GROUP PEAK PLATEAUS
    # ======================================

    # Group adjacent exposed supports of
    # the same elevation. A plateau higher
    # than its neighboring terrain receives
    # a domino at each outer edge.

    peak_groups = []
    groups = []
    current_group = []

    group_gap = BRICK_LENGTH * 1.35

    for record in support_records:

        if current_group:

            previous = current_group[-1]

            same_height = (
                abs(record["z"] - previous["z"])
                < TOLERANCE
            )

            nearby = (
                record["s"] - previous["s"]
                <= group_gap
            )

            if not (same_height and nearby):
                groups.append(current_group)
                current_group = []

        current_group.append(record)

    if current_group:
        groups.append(current_group)

    grouped_peak_ids = set()

    for group_index, group in enumerate(groups):

        first = group[0]
        last = group[-1]

        group_z = first["z"]

        before_z = height_at_distance(
            crv,
            first["s"] - BRICK_LENGTH,
            supports
        )

        after_z = height_at_distance(
            crv,
            last["s"] + BRICK_LENGTH,
            supports
        )

        is_peak = (
            group_z > before_z + TOLERANCE
            and
            group_z > after_z + TOLERANCE
        )

        if not is_peak:
            continue

        peak_groups.append(group_index)

        for record in group:
            grouped_peak_ids.add(id(record))

        # Start edge of plateau
        if first["start"] is not None:
            item = dict(first["start"])
            item["kind"] = "peak_start"
            item["priority"] = 3
            candidates.append(item)

        # End edge of plateau
        if last["end"] is not None:
            item = dict(last["end"])
            item["kind"] = "peak_end"
            item["priority"] = 3
            candidates.append(item)

    # ======================================
    # 11. UPHILL / DOWNHILL / FLAT
    # ======================================

    for record in support_records:

        if id(record) in grouped_peak_ids:
            continue

        section = classify_support(
            crv,
            record["box"],
            supports,
            BRICK_LENGTH * 0.8
        )

        # Uphill: start edge
        # Downhill: end edge
        # Flat: end edge by default

        if section == "uphill":
            preferred = record["start"]
            alternative = record["end"]

        elif section == "downhill":
            preferred = record["end"]
            alternative = record["start"]

        else:
            preferred = record["end"]
            alternative = record["start"]

        item = preferred

        # If the preferred edge is not fully
        # supported, test the opposite edge.
        if item is None:
            item = alternative

        if item is None:
            warnings.append(
                "No valid edge at curve distance "
                "{:.1f} mm".format(record["s"])
            )
            continue

        item = dict(item)

        item["kind"] = section
        item["priority"] = (
            2 if section != "flat" else 1
        )

        candidates.append(item)

    # ======================================
    # 12. FLOOR DOMINO CANDIDATES
    # ======================================

    floor_count = int(
        math.floor(curve_length / floor_spacing)
    )

    for i in range(floor_count + 1):

        s = i * floor_spacing

        x, y, tx, ty = curve_data(crv, s)

        if not valid_footprint(
            x, y, 0.0,
            tx, ty, supports
        ):
            continue

        candidates.append({
            "s": s,
            "x": x,
            "y": y,
            "z": 0.0,
            "tx": tx,
            "ty": ty,
            "kind": "floor",
            "priority": 0
        })

    # ======================================
    # 13. PRIORITY FILTER
    # ======================================

    # Peak and transition dominoes are
    # chosen before flat/floor candidates.

    candidates.sort(
        key=lambda p: (-p["priority"], p["s"])
    )

    selected = []

    for candidate in candidates:

        too_close = False

        for existing in selected:

            dx = candidate["x"] - existing["x"]
            dy = candidate["y"] - existing["y"]

            distance = math.sqrt(
                dx * dx + dy * dy
            )

            if distance < min_spacing:
                too_close = True
                break

        if too_close:
            if candidate["priority"] >= 2:
                warnings.append(
                    "Important edge rejected by "
                    "spacing at {:.1f} mm".format(
                        candidate["s"]
                    )
                )
            continue

        selected.append(candidate)

    # Restore curve order
    selected.sort(key=lambda p: p["s"])

    # ======================================
    # 14. CREATE DOMINO GEOMETRY
    # ======================================

    domino_bricks = []
    domino_frames = []
    domino_types = []

    for item in selected:

        box, frame = make_domino(
            item["x"],
            item["y"],
            item["z"],
            item["tx"],
            item["ty"]
        )

        domino_bricks.append(box)
        domino_frames.append(frame)
        domino_types.append(item["kind"])

    # ======================================
    # 15. DEBUG REPORT
    # ======================================

    type_counts = {}

    for kind in domino_types:
        type_counts[kind] = (
            type_counts.get(kind, 0) + 1
        )

    warnings.insert(
        0,
        "Domino types: {}".format(type_counts)
    )

    warnings.append(
        "Geometry preview only. "
        "Physical support, robotic clearance "
        "and domino chain reaction require testing."
    )

    return (
        domino_bricks,
        domino_frames,
        domino_types,
        warnings
    )
