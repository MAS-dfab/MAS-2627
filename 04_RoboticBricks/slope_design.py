
import math

from compas.geometry import Point, Frame, Box


# ==========================================
# 1. BRICK SETTINGS (mm)
# ==========================================

BRICK_LENGTH = 32.0
BRICK_WIDTH = 15.0
BRICK_HEIGHT = 10.0

# Remove bottom-layer groups shorter than 3
MIN_CONNECTED_BRICKS = 3

# Extra base bricks beside upper-layer supports
# 0 = only required supporting bricks
# 1 = one extra brick on either side
BASE_EXTENSION = 0


# ==========================================
# 2. GEOMETRY HELPERS
# ==========================================

def make_brick(frame):

    brick = Box(
        BRICK_LENGTH,
        BRICK_WIDTH,
        BRICK_HEIGHT
    )

    brick.frame = frame

    return brick


def frame_at_distance(crv, distance, z):

    success, t = crv.LengthParameter(
        float(distance)
    )

    if not success:
        raise ValueError(
            "Could not evaluate curve at distance"
        )

    pt = crv.PointAt(t)
    tangent = crv.TangentAt(t)

    length = math.sqrt(
        tangent.X ** 2 +
        tangent.Y ** 2
    )

    if length < 0.000001:
        raise ValueError(
            "Invalid curve tangent"
        )

    tx = tangent.X / length
    ty = tangent.Y / length

    # Brick length follows curve
    xaxis = [tx, ty, 0]

    # Brick width crosses curve
    yaxis = [-ty, tx, 0]

    return Frame(
        Point(pt.X, pt.Y, z),
        xaxis,
        yaxis
    )


# ==========================================
# 3. REMOVE ISOLATED BRICK GROUPS
# ==========================================

def remove_isolated_bricks(
    bricks,
    min_count=3
):

    if not bricks:
        return []

    if min_count <= 1:
        return list(bricks)

    groups = []
    current_group = []

    for index, frame in bricks:

        if current_group:

            previous_index = current_group[-1][0]

            if index != previous_index + 1:

                groups.append(current_group)
                current_group = []

        current_group.append(
            (index, frame)
        )

    if current_group:
        groups.append(current_group)

    filtered_bricks = []

    for group in groups:

        if len(group) >= min_count:
            filtered_bricks.extend(group)

    return filtered_bricks


# ==========================================
# 4. REMOVE UNNECESSARY BASE BRICKS
# ==========================================

def trim_base_bricks(
    all_layers,
    extension=1
):

    if len(all_layers) < 2:
        return all_layers

    # The second layer defines which
    # bottom bricks must remain.
    second_layer = all_layers[1]

    if not second_layer:
        return all_layers

    required_indices = set()

    # An upper brick at index i is supported
    # by bottom bricks i and i+1.
    for i, frame in second_layer:

        required_indices.add(i)
        required_indices.add(i + 1)

    # Keep additional base bricks
    # beside the required supports.
    allowed_indices = set()

    for i in required_indices:

        for offset in range(
            -extension,
            extension + 1
        ):

            allowed_indices.add(
                i + offset
            )

    # Remove unnecessary bottom bricks
    filtered_base = []

    for i, frame in all_layers[0]:

        if i in allowed_indices:

            filtered_base.append(
                (i, frame)
            )

    all_layers[0] = filtered_base

    return all_layers


# ==========================================
# 5. ORIGINAL SLOPE GENERATOR
# ==========================================

def generate_slope(samples, heights):

    if len(samples) != len(heights):
        raise ValueError(
            "Samples and heights must match"
        )

    slope_bricks = []
    support_frames = []
    brick_frames = []

    for i, data in enumerate(samples):

        x, y, tx, ty = data
        layers = int(heights[i])

        if layers < 0:
            raise ValueError(
                "Negative layer count"
            )

        length = math.sqrt(
            tx ** 2 + ty ** 2
        )

        if length < 0.000001:
            raise ValueError(
                "Invalid tangent"
            )

        tx /= length
        ty /= length

        # Original orientation:
        # 32 mm across curve
        xaxis = [ty, -tx, 0]
        yaxis = [tx, ty, 0]

        for layer in range(layers):

            z = (
                layer + 0.5
            ) * BRICK_HEIGHT

            frame = Frame(
                Point(x, y, z),
                xaxis,
                yaxis
            )

            slope_bricks.append(
                make_brick(frame)
            )

            brick_frames.append(frame)

        top_frame = Frame(
            Point(
                x,
                y,
                layers * BRICK_HEIGHT
            ),
            [tx, ty, 0],
            [-ty, tx, 0]
        )

        support_frames.append(top_frame)

    return (
        slope_bricks,
        support_frames,
        brick_frames
    )


# ==========================================
# 6. SHARED BONDED WALL GENERATOR
# ==========================================

def _generate_bonded_wall(
    crv,
    max_layers,
    gap,
    height_function,
    min_connected_bricks=1,
    trim_base=False,
    base_extension=1
):

    # --------------------------------------
    # VALIDATION
    # --------------------------------------

    if crv is None:
        raise ValueError(
            "No curve connected"
        )

    if gap < 0:
        raise ValueError(
            "Spacing cannot be negative"
        )

    if max_layers < 1:
        raise ValueError(
            "Maximum layers must be >= 1"
        )

    curve_length = crv.GetLength()
    pitch = BRICK_LENGTH + gap

    if curve_length < BRICK_LENGTH:
        raise ValueError(
            "Curve is too short"
        )

    number = int(
        math.floor(
            (curve_length - BRICK_LENGTH)
            / pitch
        )
    ) + 1

    all_layers = []
    previous_indices = set()

    # ======================================
    # GENERATE EACH LAYER
    # ======================================

    for layer in range(max_layers):

        current_bricks = []

        count = max(
            0,
            number - layer
        )

        for i in range(count):

            # --------------------------------
            # RUNNING BOND
            # --------------------------------

            distance = (
                BRICK_LENGTH / 2.0
                + i * pitch
                + layer * pitch / 2.0
            )

            # Desired height
            target_height = height_function(
                distance,
                curve_length
            )

            if target_height < layer + 1:
                continue

            # --------------------------------
            # CHECK LOWER SUPPORT
            # --------------------------------

            if layer > 0:

                left_support = (
                    i in previous_indices
                )

                right_support = (
                    i + 1 in previous_indices
                )

                if not (
                    left_support
                    and right_support
                ):
                    continue

            # --------------------------------
            # GENERATE FRAME
            # --------------------------------

            z = (
                layer + 0.5
            ) * BRICK_HEIGHT

            frame = frame_at_distance(
                crv,
                distance,
                z
            )

            current_bricks.append(
                (i, frame)
            )

        # ==================================
        # FILTER ISOLATED BASE GROUPS
        # ==================================

        if layer == 0:

            current_bricks = (
                remove_isolated_bricks(
                    current_bricks,
                    min_connected_bricks
                )
            )

        # ==================================
        # STORE VALID LAYER
        # ==================================

        current_indices = set(
            i for i, frame
            in current_bricks
        )

        all_layers.append(
            current_bricks
        )

        previous_indices = current_indices

    # ======================================
    # TRIM UNNECESSARY FIRST-LAYER BRICKS
    # ======================================

    if trim_base:

        all_layers = trim_base_bricks(
            all_layers,
            extension=base_extension
        )

    # ======================================
    # REBUILD FINAL GEOMETRY
    # ======================================

    slope_bricks = []
    brick_frames = []
    layer_counts = []
    support_frames = []

    for layer_bricks in all_layers:

        layer_counts.append(
            len(layer_bricks)
        )

        for i, frame in layer_bricks:

            slope_bricks.append(
                make_brick(frame)
            )

            brick_frames.append(frame)

    # ======================================
    # GENERATE EXPOSED TOP FRAMES
    # ======================================

    for layer, bricks in enumerate(all_layers):

        upper_indices = set()

        if layer + 1 < len(all_layers):

            upper_indices = set(
                i for i, frame
                in all_layers[layer + 1]
            )

        for i, frame in bricks:

            covered = (
                i in upper_indices
                or (i - 1) in upper_indices
            )

            if covered:
                continue

            top_frame = frame.copy()

            top_frame.point.z += (
                BRICK_HEIGHT / 2.0
            )

            support_frames.append(
                top_frame
            )

    return (
        slope_bricks,
        support_frames,
        brick_frames,
        layer_counts
    )


# ==========================================
# 7. ORIGINAL BONDED WALL
# ==========================================

def generate_wall(
    crv,
    num_layers=2,
    gap=1.0
):

    num_layers = int(num_layers)

    def constant_height(
        distance,
        curve_length
    ):
        return num_layers

    return _generate_bonded_wall(
        crv,
        max_layers=num_layers,
        gap=gap,
        height_function=constant_height,
        min_connected_bricks=1,
        trim_base=False
    )


# ==========================================
# 8. PARAMETRIC SLOPE WALL
# ==========================================

def generate_sloped_wall(
    crv,
    max_layers=5,
    min_layers=0,
    gap=1.0,
    num_peaks=2,
    min_peak_layers=None,
    min_connected_bricks=None,
    base_extension=None
):

    # --------------------------------------
    # PARAMETER SETTINGS
    # --------------------------------------

    max_layers = int(max_layers)
    min_layers = int(min_layers)
    num_peaks = int(num_peaks)

    if min_peak_layers is None:
        min_peak_layers = max_layers

    min_peak_layers = int(
        min_peak_layers
    )

    if min_connected_bricks is None:
        min_connected_bricks = (
            MIN_CONNECTED_BRICKS
        )

    if base_extension is None:
        base_extension = BASE_EXTENSION

    min_connected_bricks = int(
        min_connected_bricks
    )

    base_extension = int(
        base_extension
    )

    # --------------------------------------
    # VALIDATION
    # --------------------------------------

    if not (
        0 <= min_layers
        <= min_peak_layers
        <= max_layers
    ):
        raise ValueError(
            "Required: min_layers <= "
            "min_peak_layers <= max_layers"
        )

    if max_layers < 1:
        raise ValueError(
            "Maximum layers must be >= 1"
        )

    if num_peaks < 1:
        raise ValueError(
            "Number of peaks must be >= 1"
        )

    if min_connected_bricks < 1:
        raise ValueError(
            "min_connected_bricks must be >= 1"
        )

    if base_extension < 0:
        raise ValueError(
            "base_extension cannot be negative"
        )

    # ======================================
    # HEIGHT PROFILE
    # ======================================

    def get_height(
        distance,
        curve_length
    ):

        u = distance / curve_length

        u = max(
            0.0,
            min(1.0, u)
        )

        peak_index = min(
            int(u * num_peaks),
            num_peaks - 1
        )

        # Alternate high and low peaks
        if peak_index % 2 == 0:

            peak_height = max_layers

        else:

            peak_height = min_peak_layers

        wave = math.sin(
            math.pi * num_peaks * u
        ) ** 2

        height = (
            min_layers
            + (peak_height - min_layers)
            * wave
        )

        return int(
            math.floor(height + 0.5)
        )

    # ======================================
    # GENERATE SLOPE
    # ======================================

    # Trim unnecessary base bricks only
    # when the valley minimum is zero.
    should_trim = (
        min_layers == 0
    )

    return _generate_bonded_wall(
        crv,
        max_layers=max_layers,
        gap=gap,
        height_function=get_height,
        min_connected_bricks=min_connected_bricks,
        trim_base=should_trim,
        base_extension=base_extension
    )
