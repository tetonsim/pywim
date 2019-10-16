import threemf
import numpy as np

from .. import WimObject

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