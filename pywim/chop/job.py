
from . import mesh, slicer
from .. import am
from .. import WimObject, WimList

class BoundaryCondition(WimObject):
    DEFAULTTYPENAME = 'fixed'
    def __init__(self, name=None):
        self.name = name if name else 'bc'
        self.type = None
        self.face = WimList(int)

class FixedBoundaryCondition(BoundaryCondition):
    JSONTYPENAME = 'fixed'

#class SlideBoundaryCondition(BoundaryCondition):
#    JSONTYPENAME = 'slide'

class Load(WimObject):
    DEFAULTTYPENAME = 'pressure'
    def __init__(self, name=None):
        self.name = name if name else 'load'
        self.type = None
        self.face = WimList(int)

class Force(Load):
    JSONTYPENAME = 'force'
    def __init__(self, name=None):
        super().__init__(name)
        self.type = Force.JSONTYPENAME
        self.force = WimTuple(float, float, float)

class Step(WimObject):
    def __init__(self, name=None):
        self.name = name if name else 'default'
        self.boundary_conditions = WimList(BoundaryCondition)
        self.loads = WimList(Load)

class Job(WimObject):
    def __init__(self):
        self.meshes = WimList(mesh.Mesh)
        self.print_config = am.Config()
        self.steps = WimList(Step)
        self.slicer = slicer.Slicer()
