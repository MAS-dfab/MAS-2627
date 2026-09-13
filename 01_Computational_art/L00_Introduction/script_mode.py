import numpy as np
import Rhino.Geometry as rg

pts = []
for i, j in zip(np.linspace(0,1,count), np.linspace(0,1,count)):
    pts.append(rg.Point3d(i, j, 0))