import itertools
import math

try:
    import stl
    NUMPY_STL = True
except:
    NUMPY_STL = False

from typing import Dict, List, Set, Union, Callable

from . import Vertex as _Vertex
from . import Edge as _Edge
from . import InfiniteCylinder, Plane, Polygon, Vector

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

    @property
    def area(self) -> float:
        v12 = Vector.FromTwoPoints(self.v1, self.v2)
        v13 = Vector.FromTwoPoints(self.v1, self.v3)
        return 0.5 * v12.cross(v13).magnitude()

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

    @property
    def triangles(self) -> Set[Triangle]:
        '''
        Returns a set of all triangles connected to this edge
        '''
        #return set([t for t in [a.t1, a.t2] for a in self.angles])
        return set([t for a in self.angles for t in [a.t1, a.t2]])

class Mesh:
     # all angles in radians
    _COPLANAR_ANGLE = 0.002
    _MAX_EDGE_CYLINDER_ANGLE = math.pi / 6.
    _CYLINDER_RADIUS_TOLERANCE = 0.05

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

    def _select_connected_triangles(self, tri : Triangle, triangle_filter : Callable[[Triangle], bool]) -> List[Triangle]:
        '''
        Finds connected triangles who are connected via an edge that satisfies the given triangle_filter
        '''

        face = { tri }
        tris_to_check = { tri }

        while len(tris_to_check) > 0:
            t = tris_to_check.pop()
            for e in self._triangle_to_edge[t]:
                for t2 in e.triangles:
                    if t2 in face:
                        continue

                    if triangle_filter(t2):
                        face.add(t2)
                        tris_to_check.add(t2)

        return face

    def _select_connected_triangles_edge_condition(self, tri : Triangle, edge_condition : Callable[[EdgeAngle], bool]) -> List[Triangle]:
        '''
        Finds connected triangles who are connected via an edge that satisfies the given edge_condition
        '''

        face = { tri }
        tris_to_check = { tri }

        # The initial set of Triangles to check is the given Triangle.
        #
        # For each Triangle that is checked the Edges that make up the Triangle
        # are checked through the edge_condition.If the condition is met any Triangles
        # also attached to the Edge are added to the face and also added to
        # the set of Triangles to check.

        while len(tris_to_check) > 0:
            t = tris_to_check.pop()
            for e in self._triangle_to_edge[t]:
                for edge_angle in e.angles:
                    if edge_condition(edge_angle):
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

        edge_condition = lambda edge_angle: edge_angle.angle < max_angle

        return self._select_connected_triangles_edge_condition(tri, edge_condition)

    def select_face_by_normals_in_plane(self, tri : Union[Triangle, int], plane : Plane,
        max_angle : float = _COPLANAR_ANGLE, max_edge_angle : float = _MAX_EDGE_CYLINDER_ANGLE) -> List[Triangle]:
        '''
        '''
        if isinstance(tri, int):
            tri = next(t for t in self.triangles if t.id == tri)

        # TODO we're checking some triangles twice with the following logic
        # how can we filter out the already checked triangle?
        edge_condition = lambda edge_angle: \
            edge_angle.angle < max_edge_angle and \
            plane.vector_angle(edge_angle.t1.normal) < max_angle and \
            plane.vector_angle(edge_angle.t2.normal) < max_angle

        return self._select_connected_triangles_edge_condition(tri, edge_condition)

    def try_select_cylinder_face(self, tri : Union[Triangle, int], coplanar_angle : float = _COPLANAR_ANGLE,
        max_edge_angle : float = _MAX_EDGE_CYLINDER_ANGLE, radius_tol : float = _CYLINDER_RADIUS_TOLERANCE) -> List[Triangle]:

        if isinstance(tri, int):
            tri = next(t for t in self.triangles if t.id == tri)

        # First let's find a triangle connected to tri at an angle that is
        # not coplanar with the input triangle, but the angle is less than max_edge_angle
        # We need two connected triangles that are not coplanar to predict
        # the geometric parameters of the potential cylinder.
        edges = self._triangle_to_edge[tri]

        connected_tris = []

        for edge in edges:
            if len(edge.angles) > 1:
                # Not interested in edges with more than 2 tris connected
                continue
            edge_angle = edge.angles[0]
            if coplanar_angle < edge_angle.angle < max_edge_angle:
                other_tri = edge_angle.t2 if tri == edge_angle.t1 else edge_angle.t1
                mating_edge = edge
                connected_tris.append((other_tri, edge_angle))
                break

        if len(connected_tris) == 0:
            return None

        # Get the connected triangle with the largest angle
        other_tri = connected_tris[0]
        for i in range(1, len(connected_tris)):
            if connected_tris[i][1] > other_tri[1]:
                other_tri = connected_tris[i]

        # decouple into the triangle and the edge angle value
        other_tri, mating_edge = other_tri

        # Check the areas of the two triangles. If they are very different this is not a cylinder
        area_min = min(tri.area, other_tri.area)
        area_max = max(tri.area, other_tri.area)

        if area_min / area_max < 0.75:
            return None 

        # Double check that the normals of the two triangles are not too similar
        # If they are, this algorithm will not work
        n1 = tri.normal
        n2 = other_tri.normal

        if n1.dot(n2) > 0.999:
            return None

        # Compute the axis direction of the potential cylinder and a corresponding plane
        cylinder_axis = n1.cross(n2).unit()
        plane = Plane(cylinder_axis)

        t1_tangent = n1.cross(cylinder_axis).unit()

        # Find the edge that is closest to parallel with t1_tangent
        edges = self._triangle_to_edge[tri]
        #edges = edges.union(self._triangle_to_edge[other_tri])

        max_dot = 0.0
        parallel_edge = None
        vec_pointing_away = None
        for e in edges:
            e_t_dot = abs(e.vector.dot(t1_tangent))
            if e_t_dot > max_dot:
                max_dot = e_t_dot
                parallel_edge = e

                v1_tris = self._vertex_to_triangle[e.v1]
                v2_tris = self._vertex_to_triangle[e.v2]

                if tri in v1_tris and other_tri in v1_tris:
                    vec_pointing_away = Vector.FromTwoPoints(e.v1, e.v2)
                elif tri in v2_tris and other_tri in v2_tris:
                    vec_pointing_away = Vector.FromTwoPoints(e.v2, e.v1)

        assert(vec_pointing_away is not None)

        n_avg = (n1 + n2).unit()

        is_concave = vec_pointing_away.dot(n_avg) > 0.0

        # Assume the parallel edge is an edge of a regular polygon
        # https://en.wikipedia.org/wiki/Regular_polygon

        # Use the edge length and the mating angle of the two triangles to roughly
        # predict the radius of the cylinder
        radius = parallel_edge.length / (2 * math.sin(0.5 * mating_edge.angle))

        # Similarily, compute the distance from the middle of the edge to the
        # center of the potential cylinder
        mid_edge_to_center = radius * math.cos(0.5 * mating_edge.angle)

        # Now using the mid point of the edge and the distance to the center we can
        # find a point that is at the center of the potential cylinder
        mid_point = parallel_edge.point_on_edge(0.5)
        if is_concave:
            # Offset in the direction of the normal vector
            center = mid_point + tri.normal * mid_edge_to_center
        else:
            # Offset in the opposite direction of the normal vector
            center = mid_point - tri.normal * mid_edge_to_center

        # Create inner and outer cylinders to check that vertices fall between the
        # two cylinders. If they don't we assume that triangle is NOT part of the
        # potential selected cylinder
        inner_cyl = InfiniteCylinder(center, radius * (1. - radius_tol), cylinder_axis)
        outer_cyl = InfiniteCylinder(center, radius * (1. + radius_tol), cylinder_axis)

        # Setup the edge check to verify all vertices fall between the inner and outer
        triangle_filter = lambda triangle: \
            plane.vector_angle(triangle.normal) <= coplanar_angle and \
            all([ outer_cyl.inside(v) and not inner_cyl.inside(v) for v in triangle.points ])

        face = self._select_connected_triangles(tri, triangle_filter)

        if len(face) <= 2:
            # Only the original triangle and the one co-planar triangle were
            # found so this is probably not a cylinder
            return None

        return face
