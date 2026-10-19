
import math
from compas.geometry import Frame
from compas.geometry import Box


class Brick:
    # Class attribute for default brick dimensions
    LENGTH = 32.00
    WIDTH = 15.20
    HEIGHT = 9.85
    # Ensure that for a class that you want fixed dimensions, you can set them as class attributes.

    def __init__(self, frame=None):
        self.length = Brick.LENGTH
        self.width = Brick.WIDTH
        self.height = Brick.HEIGHT
        self.frame = frame

    def configuration(self, config):
        self.config = config
        if self.config == 0:
            self.length = Brick.LENGTH
            self.width = Brick.WIDTH
            self.height = Brick.HEIGHT
        elif config == 1:
            self.length = Brick.LENGTH
            self.width = Brick.HEIGHT
            self.height = Brick.WIDTH
        elif self.config == 2:
            self.length = Brick.WIDTH
            self.width = Brick.HEIGHT
            self.height = Brick.LENGTH
        else:
            raise ValueError("Invalid configuration value. Must be 0, 1, or 2.")

    def get_config(self):
        return self.config

    def __str__(self):
        return f"Brick of {self.length}mm x {self.width}mm x {self.height}mm (frame: {self.frame})"

    def draw(self):
        box = Box(self.length, self.width, self.height)
        box.frame = self.frame.copy()
        return box

    def rotate(self, rotation_in_degrees):
        self.frame.rotate(math.radians(rotation_in_degrees), (0, 0, 1), self.frame.point)

    def get_pick_frame(self):
        pick_frame = self.frame.copy()
        pick_frame.point.z += self.height / 2
        # Safety check to ensure the pick frame is oriented correctly
        if pick_frame.zaxis.z > 0:
            pick_frame.xaxis = -pick_frame.xaxis
        return pick_frame

