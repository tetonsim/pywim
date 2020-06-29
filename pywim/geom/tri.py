import itertools
import math

try:
    import stl
    NUMPY_STL = True
except:
    NUMPY_STL = False

from typing import Dict, List, Set, Union

from . import Vertex as _Vertex
from . import Vector
from . import Edge as _Edge

class _MeshEntity:
    def __init__(self, id):
        self.id = id

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

class Vertex(_MeshEntity, _Vertex):
    def __init__(self, id, *args, **kwargs):
        _MeshEntity.__init__(self, id)
        _Vertex.__init__(self, *args, **kwargs)

    def __str__(self):
        return '{} :: ({}, {}, {})'.format(self.id, self.x, self.y, self.z)

class Triangle(_MeshEntity):
    def __init__(self, id, v1, v2, v3):
        super().__init__(id)
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3
        self.normal = Triangle._compute_normal(self.v1, self.v2, self.v3)

    def __str__(self):
        return '{} :: [{}, {}, {}]'.format(self.id, self.v1.id, self.v2.id, self.v3.id)

    @staticmethod
    def _compute_normal(v1, v2, v3):
        va = Vector.FromTwoPoints(v1, v2)
        vb = Vector.FromTwoPoints(v1, v3)

        return va.cross(vb).unit()

    @property
    def points(self):
        return (self.v1, self.v2, self.v3)

    def angle(self, other : 'Triangle') -> float:
        return self.normal.unit_angle(other.normal)

class SimpleEdge:
    def __init__(self, v1 : Vertex, v2 : Vertex):
        if v1.id == v2.id:
            raise Exception('SimpleEdge cannot have matching vertices')
        self.v1 = v1 if v1.id < v2.id else v2
        self.v2 = v2 if v2.id > v1.id else v1

    def __eq__(self, other : 'SimpleEdge'):
        # assumes v1.id is always lower than v2.id
        return self.v1 == other.v1 and self.v2 == other.v2

    def __hash__(self):
        return hash((self.v1.id, self.v2.id))

class EdgeAngle:
    def __init__(self, t1 : Triangle, t2 : Triangle):
        self.t1 = t1
        self.t2 = t2
        self.angle = t1.angle(t2)

class Edge(_MeshEntity, _Edge):
    def __init__(self, id, v1 : Vertex, v2 : Vertex):
        _MeshEntity.__init__(self, id)

        if v1.id == v2.id:
            raise Exception('Edge cannot have matching vertices')
        elif v1.id < v2.id:
            _Edge.__init__(self, v1, v2)
        else:
            _Edge.__init__(self, v2, v1)

        self.angles = []

class Mesh:
    _COPLANAR_ANGLE = 0.002 # radians

    def __init__(self):
        self.vertices = []
        self.triangles = []
        self.edges = []

        self._vertex_to_triangle = {} # Dict[Vertex, Set[Triangle]]
        self._triangle_to_edge = {} # Dict[Triangle, Set[Edge]]

    def __str__(self):
        s = 'Vertices:\n'
        for v in self.vertices:
            s += str(v) + '\n'
        s += '\nTriangles\n'
        for t in self.triangles:
            s += str(t) + '\n'
        return s

    @classmethod
    def FromSTL(cls, stl_mesh, analyze_mesh=True):
        if not NUMPY_STL:
            raise ImportError('numpy-stl is missing')

        mesh = cls()

        for p in stl_mesh.points:
            vlen = len(mesh.vertices)

            for i in range(3):
                j = 3 * i
                mesh.add_vertex(vlen + i, p[j], p[j + 1], p[j + 2])

            v1 = mesh.vertices[vlen]
            v2 = mesh.vertices[vlen+1]
            v3 = mesh.vertices[vlen+2]
            
            mesh.add_triangle(vlen // 3, v1, v2, v3)

        if analyze_mesh:
            mesh.analyze_mesh()

        return mesh

    def add_vertex(self, id, x, y, z):
        self.vertices.append(Vertex(id, x, y, z))
        return self.vertices[-1]

    def add_triangle(self, id, v1, v2, v3):
        t = Triangle(id, v1, v2, v3)
        self.triangles.append(t)
        for v in (v1, v2, v3):
            if v not in self._vertex_to_triangle:
                self._vertex_to_triangle[v] = set()
            self._vertex_to_triangle[v].add(t)
        return t

    def analyze_mesh(self, remove_degenerate_triangles=True, renumber_vertices=False, renumber_triangles=True):
        self._combine_vertices(renumber_vertices)
        if remove_degenerate_triangles:
            self._remove_degenerate_triangles(renumber_triangles)
        self._compute_edges()

    def _combine_vertices(self, renumber=False):
        vhashes = dict()
        for v in self.vertices:
            hv = v.coordinate_hash()
            if hv not in vhashes:
                vhashes[hv] = set()
            vhashes[hv].add(v)

        new_verts = set(self.vertices)

        for hv, vertices in vhashes.items():
            vert_to_keep = vertices.pop()

            for v in vertices:
                new_verts.remove(v)

                for t in self._vertex_to_triangle[v]:
                    if t.v1 == v:
                        t.v1 = vert_to_keep
                    elif t.v2 == v:
                        t.v2 = vert_to_keep
                    elif t.v3 == v:
                        t.v3 = vert_to_keep

                    self._vertex_to_triangle[vert_to_keep].add(t)
                    del self._vertex_to_triangle[v]

        self.vertices = list(new_verts)

        if renumber:
            i = 0
            for v in self.vertices:
                v.id = i
                i += 1

    def _remove_degenerate_triangles(self, renumber=True):
        degenerate_tris = []
        tindex = 0
        for t in self.triangles:
            # Look for duplicate vertex ids in the triangle
            # and if any exist, mark this triangle as degenerate
            if len({t.v1.id, t.v2.id, t.v3.id}) != 3:
                degenerate_tris.append(tindex)
            tindex += 1

        if len(degenerate_tris) == 0:
            return

        degenerate_tris.reverse()

        for tid in degenerate_tris:
            self.triangles.pop(tid)

        # Renumber the triangle indices to remove any gaps
        if renumber:
            tid = 0
            for t in self.triangles:
                t.id = tid
                tid += 1

    def _compute_edges(self):
        self.edges.clear()

        edge_tris = {}

        for t in self.triangles:
            try:
                e1 = SimpleEdge(t.v1, t.v2)
                e2 = SimpleEdge(t.v2, t.v3)
                e3 = SimpleEdge(t.v3, t.v1)
            except:
                # Triangle has an invalid edge - skip it
                continue

            for e in (e1, e2, e3):
                if e in edge_tris:
                    edge_tris[e].add(t)
                else:
                    edge_tris[e] = { t }

            self._triangle_to_edge[t] = set()

        eid = 0
        for e, tris in edge_tris.items():
            edge = Edge(eid, e.v1, e.v2)
            self.edges.append(edge)

            if len(tris) == 1:
                # Only one triangle found on edge - should we do anything?
                continue

            for t1, t2 in itertools.combinations(tris, 2):
                edge.angles.append( EdgeAngle(t1, t2) )
                self._triangle_to_edge[t1].add(edge)
                self._triangle_to_edge[t2].add(edge)

            eid += 1

    def triangles_in_parallel_plane(self, tri : Union[Triangle, int], max_angle : float = _COPLANAR_ANGLE) -> List[Triangle]:
        '''
        Returns a list of Triangles that are in any plane that is co-planar to the plane
        that the given Triangle lies in. max_angle is the maximum angle to consider as
        co-planar between a Triangle and the given Triangle.
        '''
        if isinstance(tri, int):
            tri = next(t for t in self.triangles if t.id == tri)

        plane_tris = []

        for t in self.triangles:
            if tri.angle(t) < max_angle: # 0.1 degrees
                plane_tris.append(t)

        return plane_tris

    def select_planar_face(self, tri : Union[Triangle, int]) -> List[Triangle]:
        '''
        Returns a list of Triangles that are co-planar and connected with the given Triangle.
        '''

        return self.select_face_by_edge_angle(tri, Mesh._COPLANAR_ANGLE)

    def select_face_by_edge_angle(self, tri : Union[Triangle, int], max_angle : float) -> List[Triangle]:
        '''
        Returns a list of Triangles that are connected with the given Triangle and connected 
        through an Edge that is below the given max_angle. In other words Triangle normal
        vectors are compared to their neighbors and not the original Triangle to determine
        their inclusion status.
        '''
        if isinstance(tri, int):
            tri = next(t for t in self.triangles if t.id == tri)

        face = { tri }
        tris_to_check = { tri }

        # The initial set of Triangles to check is the given Triangle.
        #
        # For each Triangle that is checked the Edges that make up the Triangle
        # are checked for their angle. If the angle is below max_angle and Triangles
        # also attached to the Edge are added to the face and also added to
        # the set of Triangles to check.

        while len(tris_to_check) > 0:
            t = tris_to_check.pop()
            for e in self._triangle_to_edge[t]:
                for edge_angle in e.angles:
                    if edge_angle.angle < max_angle:
                        edge_tris = { edge_angle.t1, edge_angle.t2 }

                        # Add triangles to tris_to_check that are not in the face
                        # If a triangle is in face it has already been checked
                        tri_added = edge_tris.difference(face)

                        # Note, with this logic, it is possible for a triangle
                        # to be checked more than once. If on the first check,
                        # the edge in question exceeds max_angle, the triangle
                        # will not be added to face. But there could be another
                        # path of edges that brings the previously discarded Triangle
                        # back into the check.

                        assert len(tri_added) <= 1

                        if len(tri_added) > 0:
                            tri_added = tri_added.pop()

                            tris_to_check.add(tri_added)
                            face.add(tri_added)

        return face

    def triangles_from_ids(self, ids: List[int]) -> List[Triangle]:

        triangle_list = []

        for id in ids:
            for tri in self.triangles:
                if tri.id == id:
                    triangle_list.append(tri)
                    break

        return triangle_list