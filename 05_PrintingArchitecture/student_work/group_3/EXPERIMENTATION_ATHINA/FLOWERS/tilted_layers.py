# r: compas
"""
Tilted layers: slice the form with planes that start flat on the ground and
tilt gradually, so the layers run across the form and end at its rim
instead of running down to the ground like the surface isocurves do.

Grasshopper Python 3 component.
Inputs:
    form          Brep / Surface   the 3D form
    layer_height  float            distance between layers at the centre (mm)
    max_angle     float            final tilt in degrees (negative tilts the other way)
    axis_angle    float            direction of the tilt in plan, degrees (0 = tilt around X, 90 = around Y)
    ramp          float            height (mm) over which the tilt grows from 0 to max_angle
Outputs:
    layers        the print layers, bottom to top, all running the same direction
    planes        the cutting planes (for preview)
    info          layer count, where the layers stop, spacing check
"""
import math
import Rhino.Geometry as rg
import Grasshopper


def to_brep(geo):
    if isinstance(geo, rg.Brep):
        return geo
    if isinstance(geo, (rg.Surface, rg.Extrusion)):
        return geo.ToBrep()
    return rg.Brep.TryConvertBrep(geo)


def slice_planes(bbox, layer_height, max_angle, axis_angle, ramp):
    """One plane per layer: flat at the ground, tilting up to max_angle over `ramp` mm."""
    zmin, zmax = bbox.Min.Z, bbox.Max.Z
    centre_x, centre_y = (bbox.Min.X + bbox.Max.X) / 2.0, (bbox.Min.Y + bbox.Max.Y) / 2.0
    a = math.radians(axis_angle)
    axis = rg.Vector3d(math.cos(a), math.sin(a), 0)
    planes = []
    z = zmin + 0.2  # first layer just above the ground so the cut finds the base
    # tilted planes still hit the form above zmax on their low side, so go further;
    # the slicing loop stops at the first plane that misses the form
    while z < zmax + (zmax - zmin):
        t = min(1.0, (z - zmin) / ramp) if ramp > 0 else 1.0
        normal = rg.Vector3d(0, 0, 1)
        normal.Rotate(math.radians(max_angle) * t, axis)
        planes.append(rg.Plane(rg.Point3d(centre_x, centre_y, z), normal))
        z += layer_height
    return planes


def main_piece(brep, plane, tol):
    """Longest curve of the cut (small fragments from the curled lip are ignored)."""
    ok, crvs, pts = rg.Intersect.Intersection.BrepPlane(brep, plane, tol)
    if not ok or not crvs:
        return None
    joined = rg.Curve.JoinCurves(crvs, tol * 10)
    if not joined:
        return None
    return max(joined, key=lambda c: c.GetLength())


def gap(a, b, samples=20):
    """Shortest and longest distance from curve a to curve b."""
    ds = []
    for k in range(samples):
        p = a.PointAtNormalizedLength(k / float(samples - 1))
        ok, t = b.ClosestPoint(p)
        ds.append(p.DistanceTo(b.PointAt(t)))
    return min(ds), max(ds)


class Script_Instance(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, form, layer_height, max_angle, axis_angle, ramp):
        layer_height = float(layer_height) if layer_height else 1.5
        max_angle = float(max_angle) if max_angle is not None else 15.0
        axis_angle = float(axis_angle) if axis_angle is not None else 0.0
        ramp = float(ramp) if ramp is not None else 40.0

        brep = to_brep(form)
        if brep is None:
            return None, None, "connect a Brep/Surface to 'form'"
        tol = 0.01
        bbox = brep.GetBoundingBox(True)

        planes = slice_planes(bbox, layer_height, max_angle, axis_angle, ramp)
        layers, used_planes = [], []
        stop_reason = "reached the top"
        for plane in planes:
            crv = main_piece(brep, plane, tol)
            if crv is None:
                stop_reason = "reached the top" if layers else "first plane missed the form"
                break
            if crv.IsClosed:
                # above the rim the form curls over and the cut becomes a closed loop
                stop_reason = "cut becomes a closed loop at z={:.1f} (curled top)".format(plane.Origin.Z)
                break
            # all layers run the same way, so Dispatch/Flip downstream can zigzag them
            if layers and layers[-1].PointAtStart.DistanceTo(crv.PointAtEnd) < layers[-1].PointAtStart.DistanceTo(crv.PointAtStart):
                crv.Reverse()
            layers.append(crv)
            used_planes.append(plane)

        if len(layers) < 2:
            return layers, used_planes, "fewer than 2 layers - check the inputs"

        # measured from each layer down to the one it sits on (what supports it)
        gaps = [gap(upper, lower) for lower, upper in zip(layers[:-1], layers[1:])]
        top = max(c.GetBoundingBox(True).Max.Z for c in layers)
        info = "\n".join([
            "{} layers, stopped: {}".format(len(layers), stop_reason),
            "layers reach z={:.1f} of form top z={:.1f}".format(top, bbox.Max.Z),
            "layer spacing: min {:.2f} mm, max {:.2f} mm".format(min(g[0] for g in gaps), max(g[1] for g in gaps)),
        ])
        return layers, used_planes, info
