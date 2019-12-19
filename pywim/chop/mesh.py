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
    def __init__(self, extrusion=None, infill=None, none=None):
        self.extrusion = extrusion if extrusion else 'extrusion'
        self.infill = infill if infill else 'infill'
        self.none = none if none else 'none'

class Mesh(WimObject, threemf.mesh.Mesh):
    def __init__(self, name=None):
        super().__init__()
        self.transform = np.identity(4)
        self.name = name if name else ''
        self.type = MeshType.normal
        self.print_config = am.Config()
        self.materials = MaterialNames()

    @staticmethod
    def cast_from_base(base_mesh : threemf.mesh.Mesh):
        mesh = Mesh()
        mesh.vertices = base_mesh.vertices
        mesh.triangles = base_mesh.triangles
        return mesh

    @staticmethod
    def from_threemf_object_model(obj : threemf.model.ObjectModel):
        mesh = Mesh.cast_from_base(obj.mesh)

        mesh.materials = MaterialNames(
            '%s-extrusion' % mesh.name,
            '%s-infill' % mesh.name
        )

        # Check for cura meta data
        for md in obj.metadata:
            if not md.name.startswith('cura:'):
                continue

            name = md.name[5:]

            if name == 'infill_mesh':
                if md.value.lower() == 'true':
                    mesh.type = MeshType.infill
            else:
                mesh.print_config.from_cura_setting(name, md.value)

        return mesh

    def __to_dict__(self):
        verts = [ (v.x, v.y, v.z) for v in self.vertices ]
        tris = [ (t.v1, t.v2, t.v3) for t in self.triangles ]

        return {
            'name': self.name,
            'type': self.type.name,
            'materials': self.materials.to_dict(),
            'transform': list(self.transform.flatten()),
            'print_config': self.print_config.to_dict(),
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
