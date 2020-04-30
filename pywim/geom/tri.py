import itertools
import math

import numpy

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

    def get_neighbored_triangles(
            self,
            tri: Union[Triangle, int],
            coplanar_angle: float = _COPLANAR_ANGLE,
            max_edge_angle: float = _MAX_EDGE_CYLINDER_ANGLE
            ):

        # Convert an intenger into an Triangle if needed..
        if isinstance(tri, int):
            tri = next(t for t in self.triangles if t.id == tri)

        # Getting all neighbored triangles
        edges = self._triangle_to_edge[tri]
        connected_tris = []

        for edge in edges:
            # Not interested in edges with more than 2 tris connected
            if len(edge.angles) > 1:
                continue

            edge_angle = edge.angles[0]

            if tri == edge_angle.t1:
                other_tri = edge_angle.t2
            else:
                other_tri = edge_angle.t1
            connected_tris.append((other_tri, edge_angle))

        # List with tuples of triangles and angles
        # (relative to the provided triangle)
        return connected_tris

    def general_cylinder_check(self, this_triangle):
        # Simply checks for all known cases as known and
        # listed below
        return self.simple_cylindric_surface_check(this_triangle)  # or self.extended_cylindric_surface_check_no1(this_triangle)

    def simple_cylindric_surface_check(self, face_id):
        # Simple check, which savely detects
        # non-stacked tessellated cylinders.
        planar_selected_faces = self.select_planar_face(face_id)

        # If we found a planar face using two or less faces, it is likely,
        # that this face is a cylinder. Normally a plane consists of more
        # than two faces. However, it doesn't need to be always the case.

        return len(planar_selected_faces) <= 2

    def find_neighbored_surface_for_extended_check(
            self,
            this_triangle,
            coplanar_angle: float = _COPLANAR_ANGLE,
            max_edge_angle: float = _MAX_EDGE_CYLINDER_ANGLE,
            radius_tol: float = _CYLINDER_RADIUS_TOLERANCE
            ):
        # # Extended check, which detects stacked tessellated cylinders.
        # # That one happens e.g. if an cylindric hole is deeper
        # # than the max edge length in Autodesk Inventors STL export settings.

        # # Checking case no. 1 here. It will decide whether we need a fallback or not.

        # Convert the face_id into a Triangle object if it is an integer
        if isinstance(this_triangle, int):
            this_triangle = next(t for t in self.triangles if t.id == this_triangle)

        connected_tris = self.get_neighbored_triangles(this_triangle)
        connected_coplanar_tris = []
        connected_tris_filtered = connected_tris.copy()

        # We need to get three neighbored triangles here.
        # A valid mesh should provide this!
        if not len(connected_tris) == 3:
            return None

        # .. and filtering it as we did before.
        for entry in connected_tris:
            other_tri, edge_angle = entry
            if not coplanar_angle < edge_angle.angle:
                connected_tris_filtered.remove(entry)
                connected_coplanar_tris.append(entry)
        connected_tris = connected_tris_filtered

        # As one coplanar face should have been found before,
        # we need to get two triangles here.
        if not len(connected_tris) == 2:
            return None

        # One of the connected triangles is the top plane,
        # the other the one, which belongs to the cylinder.
        tri1_angle = connected_tris[0][1]
        tri2_angle = connected_tris[1][1]
        tri_angle_delta = abs(tri1_angle.angle - tri2_angle.angle)
        if tri_angle_delta < numpy.radians(80.0):
            print("DEBUG: tri_angle_delta < {}: {}".format(
                numpy.radians(80.0),
                tri_angle_delta)
            )
            # TODO: Adding a per layer check here: XY, XZ, YZ
            return None

        # Check the areas of the two triangles. If they are very different
        # this is not a cylinder
        print("DEBUG: this_triangle: {}".format(this_triangle))
        print("DEBUG: connected_coplanar_tris[0]: {}".format(
            connected_coplanar_tris[0]
            )
        )
        area_min = min(this_triangle.area, connected_coplanar_tris[0][0].area)
        area_max = max(this_triangle.area, connected_coplanar_tris[0][0].area)

        if area_min / area_max < 0.90:
            print("DEBUG: amin / amax < 0.90: {}".format(area_min / area_max))
            return None

        return connected_coplanar_tris[0]

    def extended_cylindric_surface_check_no1(self, this_triangle):
        # Convert the face_id into a Triangle object if it is an integer
        if isinstance(this_triangle, int):
            this_triangle = next(t for t in self.triangles if t.id == this_triangle)

        result_no1 = self.find_neighbored_surface_for_extended_check(
            this_triangle
        )
        if not result_no1:
            return False
        else:
            # If something has been found via result_no1, we need
            # to double check extended_cylindric_surface_check_no2
            return self.extended_cylindric_surface_check_no2(result_no1)

    def extended_cylindric_surface_check_no2(
            self,
            this_triangle,
            coplanar_angle: float = _COPLANAR_ANGLE,
            ):
        # # Extended check, which detects stacked tessellated cylinders.
        # # That one happens e.g. if an cylindric hole is deeper
        # # than the max edge length in Autodesk Inventors STL export settings.

        # # Checking case no. 2 here. It will decide whether we need a fallback or not.

        # Convert the face_id into a Triangle object if it is an integer
        if isinstance(this_triangle, int):
            this_triangle = next(t for t in self.triangles if t.id == this_triangle)

        connected_tris = self.get_neighbored_triangles(this_triangle)
        connected_tris_coplanar = []
        connected_tris_non_coplanar = []

        # We need to get three neighbored triangles here.
        # A valid mesh should provide this!
        if not len(connected_tris) == 3:
            return None

        # .. and filtering it as we did before.
        for entry in connected_tris:
            other_tri, edge_angle = entry
            if not coplanar_angle < edge_angle.angle:
                connected_tris_non_coplanar.append(entry)
            else:
                connected_tris_coplanar.append(entry)


        # As one coplanar face should have been found before,
        # we need to get two triangles here.
        if not len(connected_tris_non_coplanar) == 1:
            return None

        # Compared to the found triangle, one of the other triangles
        # should have a very similar triangle.
        # The area might be different, but since the cylinders are stacked
        # it should represent generally the same geometry.
        other_triangle = connected_tris_non_coplanar[0]

        neighbored_triangle_with_similar_normal_found = False
        for triangle in connected_tris_coplanar:
            neighbored_triangles = self.get_neighbored_triangles(triangle)
            for neighbored_triangle in neighbored_triangles:
                neighbored_triangle_normal = neighbored_triangle.normal
                if other_triangle.normal.dot(neighbored_triangle_normal) < math.radians(2):
                    neighbored_triangle_with_similar_normal_found = True
                    break

        if not neighbored_triangle_with_similar_normal_found:
            return False

        # Renaming some variables here, it will improve the readability below.
        this_triangle_1 = this_triangle
        other_triangle_1 = other_triangle
        this_triangle_2 = triangle
        other_triangle_2 = neighbored_triangle

        # TODO: Adding the final check whether both triangles share the same axis..
        #       1. The the difference of cylinder_axis(1)'s and cylinder_axis(2)'s radius is minimal
        #       2. Both need to be concave or not.
        #       3. Center(2) is close to the cylinder_axis(1)

        # 1. check: Simply comparing both values...
        t1_tangent_1, parallel_edge_1, vec_pointing_away_1 = self.calculate_t1_tangent_and_others(this_triangle_1, other_triangle_1)
        t1_tangent_2, parallel_edge_2, vec_pointing_away_2 = self.calculate_t1_tangent_and_others(this_triangle_2, other_triangle_2)

        radius_1 = parallel_edge_1.length / (2 * math.sin(0.5 * this_triangle_1[1].angle))
        radius_2 = parallel_edge_2.length / (2 * math.sin(0.5 * this_triangle_2[1].angle))

        radius_min = min(radius_1, radius_2)
        radius_max = max(radius_1, radius_2)

        radius_share = radius_min / radius_max
        if radius_share < 0.95:
            return False

        # 2. check: Just comparing our results on both
        is_concave_1 = vec_pointing_away_1.dot(normal_average_1) > 0.0
        is_concave_2 = vec_pointing_away_2.dot(normal_average_2) > 0.0

        # 3. check: cylinder(2)'s midpoint is close to cylinder(1)'s axis
        center_1, radius_1 = self.get_center_and_radius_of_cylinder(
            this_triangle_1,
            this_mating_edge_1,
            other_triangle_1,
            parallel_edge_1,
            vec_pointing_away_1
        )

        if is_concave_1:
            # Offset in the direction of the normal vector
            center_1 = mid_point_1 + this_triangle_1.normal * mid_edge_to_center_1
        else:
            # Offset in the opposite direction of the normal vector
            center_1 = mid_point_1 - this_triangle_1.normal * mid_edge_to_center_1
        
        if is_concave_2:
            # Offset in the direction of the normal vector
            center_2 = mid_point_2 + this_triangle_2.normal * mid_edge_to_center_2
        else:
            # Offset in the opposite direction of the normal vector
            center_2 = mid_point_2 - this_triangle_2.normal * mid_edge_to_center_2


        return True

    def calculate_t1_tangent_and_others(
            self,
            this_triangle,
            other_triangle,
            ):
        # Compute the axis direction of the potential cylinder
        # and a corresponding plane.
        cylinder_axis = this_triangle.normal.cross(other_triangle.normal).unit()
        t1_tangent = this_triangle.normal.cross(cylinder_axis).unit()

        # Find the edge that is closest to parallel with t1_tangent
        edges = self._triangle_to_edge[this_triangle]

        max_dot = 0.0
        parallel_edge = None
        vec_pointing_away = None
        for edge in edges:
            e_t_dot = abs(edge.vector.dot(t1_tangent))
            if e_t_dot > max_dot:
                max_dot = e_t_dot
                parallel_edge = edge

                v1_tris = self._vertex_to_triangle[edge.v1]
                v2_tris = self._vertex_to_triangle[edge.v2]

                if this_triangle in v1_tris and other_triangle in v1_tris:
                    vec_pointing_away = Vector.FromTwoPoints(edge.v1, edge.v2)
                elif this_triangle in v2_tris and other_triangle in v2_tris:
                    vec_pointing_away = Vector.FromTwoPoints(edge.v2, edge.v1)

        assert(vec_pointing_away is not None)

        return t1_tangent, parallel_edge, vec_pointing_away

    def get_center_and_radius_of_cylinder(
            self,
            this_triangle,
            this_mating_edge,
            other_triangle,
            parallel_edge,
            vec_pointing_away
            ):

        if this_triangle.normal.dot(other_triangle.normal) > 0.999:
            print("DEBUG: this_triangle.normal.dot(other_triangle.normal) > 0.999: {}".format(this_triangle.normal.dot(other_triangle.normal)))
            return None

        normal_average = (this_triangle.normal + other_triangle.normal).unit()

        is_concave = vec_pointing_away.dot(normal_average) > 0.0

        # Assume the parallel edge is an edge of a regular polygon
        # https://en.wikipedia.org/wiki/Regular_polygon

        # Use the edge length and the mating angle of the two triangles
        # to roughly predict the radius of the cylinder
        radius = parallel_edge.length / (2 * math.sin(0.5 * this_mating_edge.angle))

        # Similarily, compute the distance from the middle of the edge to the
        # center of the potential cylinder
        mid_edge_to_center = radius * math.cos(0.5 * this_mating_edge.angle)

        mid_point = parallel_edge.point_on_edge(0.5)

        if is_concave:
            # Offset in the direction of the normal vector
            center = mid_point + other_triangle.normal * mid_edge_to_center
        else:
            # Offset in the opposite direction of the normal vector
            center = mid_point - other_triangle.normal * mid_edge_to_center

        return center, radius

    def try_select_cylinder_face(
            self,
            this_triangle: Union[Triangle, int],
            coplanar_angle: float = _COPLANAR_ANGLE,
            max_edge_angle: float = _MAX_EDGE_CYLINDER_ANGLE,
            radius_tol: float = _CYLINDER_RADIUS_TOLERANCE
            ) -> List[Triangle]:

        # Convert an intenger into an Triangle if needed..
        if isinstance(this_triangle, int):
            this_triangle = next(t for t in self.triangles if t.id == this_triangle)

        # Getting all neighbored triangles via commonized function
        connected_tris = self.get_neighbored_triangles(this_triangle)
        connected_tris_filtered = connected_tris.copy()

        # .. and filtering them against min&max angle.
        for entry in connected_tris_filtered:
            edge_angle = entry[1]
            if not coplanar_angle < edge_angle.angle < max_edge_angle:
                connected_tris_filtered.remove(entry)
        connected_tris = connected_tris_filtered

        # Check whether there are filtered ones..
        if len(connected_tris) == 0:
            print("DEBUG: len(connected_tris) == 0: {}".format(connected_tris))
            return None

        # Get the connected triangle with the largest angle
        connected_tri = connected_tris[0]
        for i in range(1, len(connected_tris)):
            if connected_tris[i][1].angle > connected_tri[1].angle:
                connected_tri = connected_tris[i]

        # Decouple into the triangle and the edge angle value
        other_triangle, mating_edge = connected_tri

        # Check the areas of the two triangles. If they are very different
        # this is not a cylinder.
        area_min = min(this_triangle.area, other_triangle.area)
        area_max = max(this_triangle.area, other_triangle.area)

        area_share = area_min / area_max
        if area_share < 0.75:
            print("DEBUG: area_min / area_max < 0.75: {}".format(area_share))
            return None

        # Double check that the normals of the two triangles are
        # not too similar. If they are, this algorithm will not work.
        if this_triangle.normal.dot(other_triangle.normal) > 0.999:
            print("DEBUG: this_triangle.dot(other_triangle.normal) > 0.999: {}".format(this_triangle.normal.dot(other_triangle.normal)))
            return None

        # Compute the axis direction of the potential cylinder
        # and a corresponding plane.
        cylinder_axis = this_triangle.normal.cross(other_triangle.normal).unit()
        plane = Plane(cylinder_axis)

        t1_tangent, parallel_edge, vec_pointing_away = self.calculate_t1_tangent_and_others(this_triangle, other_triangle)

        center, radius = self.get_center_and_radius_of_cylinder(
            this_triangle,
            mating_edge,
            other_triangle,
            parallel_edge,
            vec_pointing_away
        )

        # Create inner and outer cylinders to check that vertices fall between the
        # two cylinders. If they don't we assume that triangle is NOT part of the
        # potential selected cylinder
        inner_cyl = InfiniteCylinder(center, radius * (1. - radius_tol), cylinder_axis)
        outer_cyl = InfiniteCylinder(center, radius * (1. + radius_tol), cylinder_axis)

        # Setup the edge check to verify all vertices fall between the inner and outer
        triangle_filter = lambda triangle: \
            plane.vector_angle(triangle.normal) <= coplanar_angle and \
            all([ outer_cyl.inside(v) and not inner_cyl.inside(v) for v in triangle.points ])

        face = self._select_connected_triangles(this_triangle, triangle_filter)

        if len(face) <= 2:
            # Only the original triangle and the one co-planar triangle were
            # found so this is probably not a cylinder
            print("DEBUG: len(face) <= 2: {}".format(repr(face)))

            return None

        return face

    def triangles_from_ids(self, ids: List[int]) -> List[Triangle]:

        triangle_list = []

        for id in ids:
            for tri in self.triangles:
                if tri.id == id:
                    triangle_list.append(tri)
                    break

        return triangle_list