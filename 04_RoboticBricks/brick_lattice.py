# IMPORTS

import math

from compas.geometry import Frame, Box

# CLASS
class Brick:
    # ===================================================
    # DEFAULT DIMENSIONS - CLASS ATTRIBUTES
    # ===================================================
    LENGTH = 32.0
    WIDTH = 15.0
    HEIGHT = 10.0
    GAP = 2.0

    # ===================================================
    # OPERATIONS ON A BRICK - INSTANCE METHODS
    # ===================================================

    def __init__(self, frame=None):
        self.length = Brick.LENGTH
        self.width = Brick.WIDTH
        self.height = Brick.HEIGHT
        self.frame = (
            frame.copy()
            if frame is not None
            else Frame.worldXY()
        )

        self.pickup_axis = "Z"

    def __str__(self):
        return f"Brick of {self.length}mm x {self.width}mm x {self.height}mm (frame: {self.frame})"

    def draw(self):
        box = Box(self.length, self.width, self.height)
        box.frame = self.frame.copy()
        return box

    def rotate(self, angle, axis="z", local=True):
        angle_rad = math.radians(angle)

        if local:
            axes = {
                "x": self.frame.xaxis,
                "y": self.frame.yaxis,
                "z": self.frame.zaxis
            }
        else:
            axes = {
                "x": [1, 0, 0],
                "y": [0, 1, 0],
                "z": [0, 0, 1]
            }

        if axis not in axes:
            raise ValueError("Invalid rotation axis")

        self.frame.rotate(angle_rad, axes[axis], self.frame.point)

    def get_frame(self):
        return self.frame.copy()
    
    def get_pick_frame(self):

        pick_frame = self.frame.copy()

        # Select pickup direction and distance
        if self.pickup_axis == "X":
            pickup_direction = self.frame.xaxis
            offset = self.length / 2.0

        elif self.pickup_axis == "Y":
            pickup_direction = self.frame.yaxis
            offset = self.width / 2.0

        elif self.pickup_axis == "Z":
            pickup_direction = self.frame.zaxis
            offset = self.height / 2.0

        else:
            raise ValueError("Invalid pickup axis")

        # Move pickup origin to selected face
        pick_frame.point += pickup_direction * offset

        # Reorient frame so its local Z follows pickup direction
        pick_frame = self.orient_pick_frame(
            pick_frame,
            self.pickup_axis
        )

        return pick_frame

    @staticmethod
    def orient_pick_frame(frame, pickup_axis="Z"):

        origin = frame.point

        x = frame.xaxis
        y = frame.yaxis
        z = frame.zaxis

        if pickup_axis == "Z":
            return frame.copy()

        elif pickup_axis == "X":
            return Frame(origin, y, z)

        elif pickup_axis == "Y":
            return Frame(origin, z, x)

        else:
            raise ValueError("Invalid pickup axis")

    # ===================================================
    # PREDEFINED BRICK CONFIGURATIONS - CLASS METHODS
    # ===================================================

    @classmethod
    def b1(cls, frame):

        brick = cls(frame)
        return brick

    @classmethod
    def b2(cls, frame):

        brick = cls(frame)
        brick.rotate(90, "z")
        return brick

    @classmethod
    def b3(cls, frame):

        brick = cls(frame)
        brick.rotate(90, "x")
        brick.rotate(180, "z", local = False)

        brick.pickup_axis = "Y"

        return brick

    @classmethod
    def b4(cls, frame):

        brick = cls(frame)
        brick.rotate(90, "x")
        brick.rotate(90, "z", local = False)

        brick.pickup_axis = "Y"
    
        return brick

    @classmethod
    def b5(cls, frame):
        
        brick = cls(frame)
        brick.rotate(90, "y")
        brick.rotate(90, "z", local = False)
        return brick

    @classmethod
    def b6(cls, frame):

        brick = cls(frame)
        brick.rotate(90, "y")
        brick.rotate(0, "z", local = False)
        return brick