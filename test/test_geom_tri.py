import unittest
import math
import numpy
from pywim import geom

from . import stl_loader

class EdgeAngleTest(unittest.TestCase):
    def setUp(self):
        self.v2 = geom.tri.Vertex(2, 1., 0., 0.)
        self.v3 = geom.tri.Vertex(3, 1., 1., 0.)
        self.v4 = geom.tri.Vertex(4, 0., 1., 0.)

    def _make_edge_angle(self, z):
        v1 = geom.tri.Vertex(1, 0., 0., z)

        t1 = geom.tri.Triangle(1, v1, self.v2, self.v4)
        t2 = geom.tri.Triangle(2, self.v2, self.v3, self.v4)

        return geom.tri.EdgeAngle(t1, t2)

    def test_coplanar(self):
        a = self._make_edge_angle(0.)

        self.assertAlmostEqual(a.angle, 0.)
        self.assertAlmostEqual(a.face_angle, math.pi)

    def test_concave(self):
        a = self._make_edge_angle(0.1)

        self.assertLess(a.face_angle, math.pi)

    def test_convex(self):
        a = self._make_edge_angle(-0.1)

        self.assertGreater(a.face_angle, math.pi)

class CubeBasic(unittest.TestCase):
    def setUp(self):
        stl_mesh = stl_loader.load_from_file('cube.stl')
        self.mesh = geom.tri.Mesh.FromSTL(stl_mesh, False)

    def test_stl_load(self):
        self.assertEqual(len(self.mesh.vertices), 12*3)
        self.assertEqual(len(self.mesh.triangles), 12)

class Cube(unittest.TestCase):
    def setUp(self):
        stl_mesh = stl_loader.load_from_file('cube.stl')
        self.mesh = geom.tri.Mesh.FromSTL(stl_mesh, True)

    def test_stl_load(self):
        self.assertEqual(len(self.mesh.vertices), 8)
        self.assertEqual(len(self.mesh.triangles), 12)

    def _select_face(self, tri0, expected_tris):
        face = self.mesh.select_planar_face(tri0)

        self.assertEqual(len(face.triangles), len(expected_tris))

        for t_sel in face.triangles:
            self.assertTrue(t_sel.id in expected_tris)

    def test_select_faces(self):
        self._select_face(0, (0, 1))
        self._select_face(1, (0, 1))

        self._select_face(10, (10, 11))
        self._select_face(11, (10, 11))

class IllFormedSTL(unittest.TestCase):
    def test_remove_degenerate_tris(self):
        stl_mesh = stl_loader.load_from_file('shelf_bracket.stl')

        mesh = geom.tri.Mesh.FromSTL(stl_mesh, False)
        mesh.analyze_mesh(remove_degenerate_triangles=True)

        self.assertEqual(len(mesh.triangles), 276)

    def test_leave_degenerate_tris(self):
        stl_mesh = stl_loader.load_from_file('shelf_bracket.stl')

        mesh = geom.tri.Mesh.FromSTL(stl_mesh, False)
        mesh.analyze_mesh(remove_degenerate_triangles=False)

        self.assertEqual(len(mesh.triangles), 284)
