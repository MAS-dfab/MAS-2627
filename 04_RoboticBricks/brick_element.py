
import math
from compas.geometry import Frame
from compas.geometry import Box, Point



class Brick:
    # Class attribute for default brick dimensions
    LENGTH = 32.0
    WIDTH = 15.0
    HEIGHT = 10.0
    # TYPES = ["laying", "standing"]

    def __init__(self, frame=None,brick_type="laying"):
        if brick_type == "laying":
            default_frame = Frame.worldXY()
        elif brick_type == "standing":
            default_frame = Frame.worldYZ()
        elif brick_type == "side":
            default_frame = Frame.worldZX()
        else:
            raise ValueError("Invalid brick type: {}".format(brick_type))
        self.length = Brick.LENGTH
        self.width = Brick.WIDTH
        self.height = Brick.HEIGHT
        self.frame = frame if frame is not None else default_frame
        self.type= brick_type

    def __str__(self):
        return f"Brick_{self.type} of {self.length}mm x {self.width}mm x {self.height}mm (frame: {self.frame})"

    # Not really necessary
    @property
    def role(self):
        return "laying" if abs(self.frame.zaxis.z) > 0.5 else "standing"


    def draw(self):
        if self.type == "laying":
            box = Box(self.length, self.width, self.height)
        elif self.type == "standing":
            box = Box(self.height, self.width, self.length)
        elif self.type == "side":
            box = Box(self.length, self.height, self.width)
        box.frame = self.frame.copy()
        return box

    def rotate(self, rotation_in_degrees):
        self.frame.rotate(math.radians(rotation_in_degrees), (0, 0, 1), self.frame.point)

    def top_frame(self):
        if self.type == "laying":
            pick_frame = self.frame.copy()
            pick_frame.point.z += self.height / 2
        elif self.type == "standing":
            pick_frame = self.frame.copy()
            pick_frame.point.z += self.length /2
        elif self.type == "side":
            pick_frame = self.frame.copy()
            pick_frame.point.z += self.width /2
        if pick_frame.zaxis.z > 0:
            pick_frame.xaxis = -pick_frame.xaxis
        return pick_frame

class PickStack:

    def stacks_for_standing(pick_frame, row=15, col=4):
        s_stacks = []
        for i in range(row):
            for j in range(col):
                x = (pick_frame.point.x + 10) - i * Brick.HEIGHT
                y = (pick_frame.point.y) - j * Brick.WIDTH
                z = (pick_frame.point.z - Brick.HEIGHT) + Brick.LENGTH
                pt = Point(x, y, z)
                frame = Frame(pt, pick_frame.xaxis, pick_frame.yaxis)
                s_stacks.append(frame)
        return s_stacks


    # stacks for standing bricks
    def stacks_for_laying(pick_frame, row=5, col=4, layers=2):
        l_stacks = []
        for k in range(layers):
            for i in range(row):
                for j in range(col):
                    x = pick_frame.point.x - i * Brick.LENGTH
                    y = pick_frame.point.y - j * Brick.WIDTH
                    z = pick_frame.point.z + (layers - k -1) * Brick.HEIGHT
                    pt = Point(x, y, z)
                    frame = Frame(pt, pick_frame.xaxis, pick_frame.yaxis)
                    l_stacks.append(frame)
        return l_stacks

