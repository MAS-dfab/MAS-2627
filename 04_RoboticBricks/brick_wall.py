
import math
from compas.geometry import Frame
from compas.geometry import Vector
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
        # This script enables us to flip dimensions so that we can reposition the brick in different orientations. 
        # The config parameter determines how the dimensions are assigned.
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

    @staticmethod
    # @staticmethod is a built-in decorator whereby method does not receive implicit first argument (i.e, self/cls)
    # This means that the method can be called on the class itself, rather than on an instance of the class.
    def clash(f1, f2, size_x, size_y):
        d = f2.point - f1.point
        # calculating distance between frame centers
        for ax in (f1.xaxis, f1.yaxis, f2.xaxis, f2.yaxis):
            reach = sum(size_x / 2 * abs(ax.dot(f.xaxis)) + size_y / 2 * abs(ax.dot(f.yaxis)) for f in (f1, f2))
            # calculating projection of the distance vector onto the axis and comparing it to the reach
            if abs(d.dot(ax)) >= reach:
                return False
        return True

    @staticmethod
    def slack(f1, f2, size_x, size_y):
        d = f2.point - f1.point
        # calculating distance between frame centers
        u = d.unitized()
        best = None
        for ax in (f1.xaxis, f1.yaxis, f2.xaxis, f2.yaxis):
            c = abs(u.dot(ax))
            # calculating projection of distance vector onto the axis
            if c > 1e-9:
                reach = sum(size_x / 2 * abs(ax.dot(f.xaxis)) + size_y / 2 * abs(ax.dot(f.yaxis)) for f in (f1, f2))
                # calculating reach along the axis of the frame
                best = reach / c if best is None else min(best, reach / c)
                # updating the best reach value if the current reach is smaller
        return d.length - best

    def clash_with(self, other, gap=0.0):
        return Brick.clash(self.frame, other.frame, self.length + gap, self.width + gap)

    def move(self, location):
        translate_vector = Vector.from_start_end(self.frame.point, location)
        self.frame.point += translate_vector

    def rotate(self, rotation_in_degrees, axis):
        self.frame.rotate(math.radians(rotation_in_degrees), axis, self.frame.point)

    def get_pick_frame(self):
        pick_frame = self.frame.copy()
        pick_frame.point.z += self.height / 2
        # Safety check to ensure the pick frame is oriented correctly
        if pick_frame.zaxis.z > 0:
            pick_frame.xaxis = -pick_frame.xaxis
        return pick_frame

