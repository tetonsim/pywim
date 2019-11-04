
from . import mesh, slicer
from .. import am
from .. import WimObject, WimList, WimTuple

class BoundaryCondition(WimObject):
    DEFAULTTYPENAME = 'fixed'
    def __init__(self, name=None, mesh=None, face=None):
        self.name = name if name else 'bc'
        self.type = None
        self.mesh = mesh if mesh else ''
        self.face = WimList(int)

        if face:
            self.face.extend(face)

class FixedBoundaryCondition(BoundaryCondition):
    JSONTYPENAME = 'fixed'

#class SlideBoundaryCondition(BoundaryCondition):
#    JSONTYPENAME = 'slide'

class Load(WimObject):
    DEFAULTTYPENAME = 'force'
    def __init__(self, name=None, mesh=None, face=None):
        self.name = name if name else 'load'
        self.type = None
        self.mesh = mesh if mesh else ''
        self.face = WimList(int)

        if face:
            self.face.extend(face)

class Force(Load):
    JSONTYPENAME = 'force'
    def __init__(self, name=None, mesh=None, face=None, force=None):
        super().__init__(name, mesh, face)
        self.type = Force.JSONTYPENAME
        self.force = WimTuple(float, float, float)

        if force:
            self.force.set(force)

class Step(WimObject):
    def __init__(self, name=None):
        self.name = name if name else 'default'
        self.boundary_conditions = WimList(BoundaryCondition)
        self.loads = WimList(Load)

class Model(WimObject):
    def __init__(self):
        self.meshes = WimList(mesh.Mesh)
        self.print_config = am.Config()
        self.steps = WimList(Step)
        self.slicer = slicer.Slicer()
