"""
Move the form so its base starts exactly at the end of the start line.

The form can first be turned in plan (around the vertical axis, about the middle of its base).
Then the base edge of the form (v = min) is attached at the end of the line, using the base corner
that makes the base continue away from the line instead of lying back on top of it.

Inputs:
    form    the surface (single-face brep or surface)
    line    the start line, in print order (it is printed from its start to its end)
    rotate  turn the form in plan by this many degrees before attaching it (0 = as drawn)
Outputs:
    moved   the moved form
    vector  the move
    info    summary
"""
import math
import Rhino.Geometry as rg
import Grasshopper


class Script_Instance(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, form, line, rotate):
        if form is None or line is None:
            return None, None, "connect form and line"
        brep = (form if isinstance(form, rg.Brep) else form.ToBrep()).DuplicateBrep()
        angle = float(rotate) if rotate else 0.0
        if angle:
            base = brep.Faces[0].IsoCurve(0, brep.Faces[0].Domain(1).Min)
            centre = (base.PointAtStart + base.PointAtEnd) / 2.0
            brep.Rotate(math.radians(angle), rg.Vector3d.ZAxis, centre)

        face = brep.Faces[0]
        base = face.IsoCurve(0, face.Domain(1).Min)
        start, end = line.PointAtStart, line.PointAtEnd
        a, b = base.PointAtStart, base.PointAtEnd

        # attach the corner whose other corner then lands farther from the line start
        best = None
        for attach, other in ((a, b), (b, a)):
            v = end - attach
            far = (other + v).DistanceTo(start)
            if best is None or far > best[0]:
                best = (far, v)
        vector = best[1]

        brep.Translate(vector)
        info = "turned {:.0f} deg, moved by ({:.1f}, {:.1f}, {:.1f}) mm, base now starts at the end of the line".format(
            angle, vector.X, vector.Y, vector.Z)
        return brep, vector, info
