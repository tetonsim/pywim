import threemf
import enum
import numpy as np

from .. import am
from .. import WimObject, WimList

class MeshType(enum.Enum):
    unknown = 0
    normal = 1
    infill = 2
    cutting = 3

class MaterialNames(WimObject):
    def __init__(self):
        self.extrusion = ''
        self.infill = ''

class Mesh(WimObject, threemf.mesh.Mesh):
    def __init__(self, name=None):
        super().__init__()
        self.transform = np.identity(4)
        self.name = name if name else ''
        self.type = MeshType.normal
        self.print_config = None
        self.slicer_settings = {}
        self.materials = MaterialNames()

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
            'name': self.name,
            'type': self.type.name,
            'materials': self.materials.to_dict(),
            'transform': list(self.transform.flatten()),
            'vertices': verts,
            'triangles': tris,
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

        m.materials = MaterialNames.from_dict(d.get('materials', {}))
        m.type = MeshType[d.get('type', MeshType.normal.name)]

        if 'print_config' in d.keys():
            m.print_config = am.Config.from_dict(d['print_config'])

        return m
