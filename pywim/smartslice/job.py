import enum
import numpy as np
import threemf

from .. import am
from .. import Meta, WimObject, WimList, WimTuple, WimIgnore
from .. import model

from . import machine, opt, slicer

class Mesh(WimObject, threemf.mesh.Mesh):
    def __init__(self):
        super().__init__()
        self.transform = np.identity(4)

    @staticmethod
    def cast_from_base(base_mesh):
        m = Mesh()
        m.vertices = base_mesh.vertices
        m.triangles = base_mesh.triangles
        return m

    def __to_dict__(self):
        verts = [ (v.x, v.y, v.z) for v in self.vertices ]
        tris = [ (t.v1, t.v2, t.v3) for t in self.triangles ]

        return {
            'vertices': verts,
            'triangles': tris,
            'transform': list(self.transform.flatten())
        }

    @classmethod
    def __from_dict__(cls, d):
        m = cls()

        for v in d['vertices']:
            m.vertices.append(
                threemf.mesh.Vertex(v[0], v[1], v[2])
            )

        for t in d['triangles']:
            m.triangles.append(
                threemf.mesh.Triangle(t[0], t[1], t[2])
            )

        m.transform = np.array(d['transform']).reshape(4, 4)

        return m

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

class JobType(enum.Enum):
    validation = 1
    optimization = 2

class Job(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.type = JobType.validation
        self.print_config = am.Config()
        self.mesh = Mesh()
        self.bulk = model.Material()
        self.steps = WimList(Step)
        self.slicer = slicer.Slicer()
        self.optimization = opt.Optimization()
