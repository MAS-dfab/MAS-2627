# region ---IMPORTS---
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

# endregion

# region ----FUNCTIONS---
"""
PrintPoint: one target for the robot
PrintPath: an ordered list of printpoints
Units: mm for positions, mm/s for speed
"""

class PrintPoint:
    """A single point in the print path, with position, orientation, speed, blend radius, and extruder state.
        Attributes:
            frame: Frame, position + orientation of the tool
            layer_index: int, which layer this point belongs to
            speed: float, robot speed in mm/s
            blend_radius: float, mm, 0 = stop exactly at the point
            is_extruder_on: bool, True while printing, False when travelling
            aspeed_io: int, which io to turn on for extrusion speed
    """
    def __init__(self, frame, layer_index=0, speed=10.0, blend_radius=0.0, is_extruder_on=True, aspeed_io=0):
        self.frame = frame                    # position + orientation of the tool
        self.layer_index = layer_index        # which layer this point belongs to
        self.speed = speed                    # robot speed in mm/s
        self.blend_radius = blend_radius      # mm, 0 = stop exactly at the point
        self.is_extruder_on = is_extruder_on  # True while printing, False when travelling
        self.aspeed_io = aspeed_io            # which aspeed_io to use

    def __str__(self):
        return f"PrintPoint (layer: {self.layer_index}, speed: {self.speed}, extruder on: {self.is_extruder_on}, aspeed_io: {self.aspeed_io}, frame: {self.frame})"

    def copy(self):
        return PrintPoint(self.frame.copy(), self.layer_index, self.speed, self.blend_radius, self.is_extruder_on, self.aspeed_io)
    
    def to_dict(self):
        return {
            "frame": [list(self.frame.point), list(self.frame.xaxis), list(self.frame.yaxis)],
            "layer_index": self.layer_index,
            "speed": self.speed,
            "blend_radius": self.blend_radius,
            "is_extruder_on": self.is_extruder_on,
            "aspeed_io": self.aspeed_io
        }

    @classmethod
    def from_dict(cls, data):
        point, xaxis, yaxis = data["frame"]
        frame = Frame(Point(*point), Vector(*xaxis), Vector(*yaxis))
        return cls(frame, data["layer_index"], data["speed"], data["blend_radius"], data["is_extruder_on"], data["aspeed_io"])

class PrintPath:
    """An ordered list of PrintPoints, representing the entire print path.
        Attributes:
            printpoints: list of PrintPoint objects
    """
    def __init__(self, printpoints):
        self.printpoints = list(printpoints)

    def __str__(self):
        return f"PrintPath with {len(self.printpoints)} printpoints"

    def __len__(self):
        return len(self.printpoints)

    def add_safety_before(self, distance=100.0, speed = 10.0):
        # a travel point above the first printpoint, so the robot approaches from above
        first = self.printpoints[0]
        self.printpoints.insert(0, self.make_safety_printpoint(first, distance, speed))

    def add_safety_after(self, distance=100.0, speed = 10.0):
        # a travel point above the last printpoint, so the robot leaves upwards
        last = self.printpoints[-1]
        self.printpoints.append(self.make_safety_printpoint(last, distance, speed))

    def make_safety_printpoint(self, printpoint, distance, speed):
        # same orientation as its neighbour, lifted straight up (world z), extruder off, no blend
        # tip: add safety points before transforming the path to the robot base
        point = printpoint.frame.point + Vector(0, 0, distance)
        frame = Frame(point, printpoint.frame.xaxis, printpoint.frame.yaxis)
        return PrintPoint(frame, printpoint.layer_index, speed, 0.0, False)

    def calculate_blend_radii(self, max_blend_radius=10.0):
        # calculate blend radii for all printpoints, based on the distance to the next point
        for i in range(len(self.printpoints) - 1):
            p1 = self.printpoints[i]
            p2 = self.printpoints[i + 1]
            distance = p1.frame.point.distance_to(p2.frame.point)
            p1.blend_radius = min(distance / 2.1, max_blend_radius)
        self.printpoints[-1].blend_radius = 0.0  # last point has no blend

    def to_dict(self):
        return {"printpoints": [printpoint.to_dict() for printpoint in self.printpoints]}

    @classmethod
    def from_dict(cls, data):
        return cls([PrintPoint.from_dict(item) for item in data["printpoints"]])

# endregion