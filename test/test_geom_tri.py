import unittest
import math
import numpy
from pywim import geom

from . import stl_loader

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

        self.assertEqual(len(face), len(expected_tris))

        for t_sel in face:
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
