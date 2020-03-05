import unittest
import math
import numpy
from pywim import geom

class VertexTest(unittest.TestCase):
    def setUp(self):
        self.v1 = geom.Vertex(1.1, 2.5, -3.4)
        self.v2 = geom.Vertex(-5.0, 1.0, 0.5)

    def test_points(self):
        p3 = self.v1.point
        p2 = self.v1.point2D

        self.assertEqual(p3[0], 1.1)
        self.assertEqual(p3[1], 2.5)
        self.assertEqual(p3[2], -3.4)

        self.assertEqual(p2[0], 1.1)
        self.assertEqual(p2[1], 2.5)

    def test_mid_point(self):
        mp = self.v1.mid_point(self.v2)

        self.assertEqual(mp.x, -1.95)
        self.assertEqual(mp.y, 1.75)
        self.assertEqual(mp.z, -1.45)

    def test_distance(self):
        d = self.v1.distance_to(self.v2)

        self.assertAlmostEqual(d, 7.39392, delta=1.0E-5)

    def test_move_by_vector(self):
        vec = geom.Vector(2.0, -1.0, 0.5)

        self.assertEqual(self.v1 + vec, geom.Vertex(3.1, 1.5, -2.9))

        va = self.v1 - vec
        vb = self.v1 + (-vec)

        vm = geom.Vertex(-0.9, 3.5, -3.9)

        self.assertAlmostEqual(va.x, vm.x)
        self.assertAlmostEqual(va.y, vm.y)
        self.assertAlmostEqual(va.z, vm.z)

        self.assertAlmostEqual(vb.x, vm.x)
        self.assertAlmostEqual(vb.y, vm.y)
        self.assertAlmostEqual(vb.z, vm.z)


class VectorTest(unittest.TestCase):
    def setUp(self):
        self.vec1 = geom.Vector(1.0, 0.0, 0.0)
        self.vec2 = geom.Vector(0.0, 1.0, 0.0)

    def test_cross_product(self):
        vecA = self.vec1.cross(self.vec2)
        vecB = self.vec2.cross(self.vec1)

        self.assertEqual(vecA.r, 0.0)
        self.assertEqual(vecA.s, 0.0)
        self.assertEqual(vecA.t, 1.0)

        self.assertEqual(vecB.r, 0.0)
        self.assertEqual(vecB.s, 0.0)
        self.assertEqual(vecB.t, -1.0)

    def test_angle(self):
        self.assertEqual(math.degrees(self.vec1.angle(self.vec2)), 90.0)

    def test_scale(self):
        self.assertEqual(geom.Vector(1.0, 2.0, 3.0) * 4, geom.Vector(4.0, 8.0, 12.0))
        self.assertEqual(4.0 * geom.Vector(1.0, 2.0, 3.0), geom.Vector(4.0, 8.0, 12.0))

class TransformationTest(unittest.TestCase):
    def setUp(self):
        self.delta = 1.0E-5
        self.alpha1 = geom.Transformation.FromAngles(theta=math.pi / 2, phi=0.0)
        self.alpha2 = geom.Transformation(0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 10.0, 20.0, 30.0)

    def test_alphaij(self):
        a_correct = numpy.array((
            (0.0, -1.0, 0.0, 0.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ))

        a = self.alpha1.alpha

        numpy.testing.assert_allclose(a, a_correct, atol=self.delta)

    def test_translation_to_and_back(self):
        v = self.alpha2.transform(geom.Vertex(0.0, 0.0, 0.0))

        self.assertEqual(v.x, 10.0)
        self.assertEqual(v.y, 20.0)
        self.assertEqual(v.z, 30.0)

        v0 = self.alpha2.inverse().transform(v)

        self.assertEqual(v0.x, 0.0)
        self.assertEqual(v0.y, 0.0)
        self.assertEqual(v0.z, 0.0)

    def test_from_three_points(self):
        alpha = geom.Transformation.FromThreePoints(
            geom.Vertex(5.0, 2.0, 9.0),
            geom.Vertex(5.0, 3.0, 9.0),
            geom.Vertex(4.5, 2.5, 9.0))

        self.assertEqual(alpha.transform(geom.Vertex(5.0, 2.0, 9.0)), geom.Vertex(0.0, 0.0, 0.0))
        self.assertEqual(alpha.transform(geom.Vertex(6.0, 3.0, 0.0)), geom.Vertex(1.0, -1.0, -9.0))

class EdgeTest(unittest.TestCase):
    def setUp(self):
        self.edge1 = geom.Edge(geom.Vertex(0.0, 0.0, 0.0), geom.Vertex(10.0, 0.0, 0.0))
        self.edge2 = geom.Edge(geom.Vertex(0.0, 1.0, 0.0), geom.Vertex(10.0, 1.0, 0.0))
        self.edge3 = geom.Edge(geom.Vertex(5.0, -5.0, 0.0), geom.Vertex(6.0, 0.5, 0.0))
        self.edge4 = geom.Edge(geom.Vertex(5.0, -5.0, 0.0), geom.Vertex(6.0, 1.0, 0.0))
        self.edge5 = geom.Edge(geom.Vertex(-5.0, 0.0, 0.0), geom.Vertex(5.0, 0.0, 0.0))
        self.edge6 = geom.Edge(geom.Vertex(-1.8, -2.8, -10.0), geom.Vertex(1.8, 0.8, -10.0))

        self.edge7 = geom.Edge(geom.Vertex(0., 0., 0.), geom.Vertex(1., 0., 0.))
        self.edge8 = geom.Edge(geom.Vertex(2., 0., 0.), geom.Vertex(3., 0., 0.))

    def test_point_on_edge(self):
        for edge in (self.edge1, self.edge2, self.edge3, self.edge4):
            self.assertEqual(edge.point_on_edge(0.0), edge.v1)
            self.assertEqual(edge.point_on_edge(1.0), edge.v2)
            self.assertEqual(edge.point_on_edge(0.5), edge.v2.mid_point(edge.v1))

    def test_collinear(self):
        v = geom.Vertex(5.0, 0.0, 0.0)
        self.assertTrue(self.edge1.collinear(v))
        self.assertFalse(self.edge4.collinear(v))

    def test_intersects(self):
        self.assertFalse(self.edge1.intersects(self.edge2))
        self.assertTrue(self.edge1.intersects(self.edge3))
        self.assertFalse(self.edge2.intersects(self.edge3))
        self.assertFalse(self.edge2.intersects(self.edge4))
        self.assertTrue(self.edge2.intersects(self.edge4, True))

        # Edge.intersects doesn't work with edges in 3D right now
        # self.assertFalse(self.edge5.intersects(self.edge6))
        # self.assertFalse(self.edge6.intersects(self.edge5))

    def test_min_distance(self):
        self.assertAlmostEqual(self.edge1.minimum_distance_to_edge(self.edge2), 1.0)
        self.assertAlmostEqual(self.edge2.minimum_distance_to_edge(self.edge1), 1.0)

        self.assertAlmostEqual(self.edge1.minimum_distance_to_edge(self.edge3), 0.0)
        self.assertAlmostEqual(self.edge3.minimum_distance_to_edge(self.edge1), 0.0)

        self.assertAlmostEqual(self.edge2.minimum_distance_to_edge(self.edge3), 0.5)
        self.assertAlmostEqual(self.edge3.minimum_distance_to_edge(self.edge2), 0.5)

        self.assertAlmostEqual(self.edge2.minimum_distance_to_edge(self.edge4), 0.0)
        self.assertAlmostEqual(self.edge4.minimum_distance_to_edge(self.edge2), 0.0)

        self.assertAlmostEqual(self.edge3.minimum_distance_to_edge(self.edge4), 0.0)
        self.assertAlmostEqual(self.edge4.minimum_distance_to_edge(self.edge3), 0.0)

        self.assertAlmostEqual(self.edge7.minimum_distance_to_edge(self.edge8), 1.0)
        self.assertAlmostEqual(self.edge8.minimum_distance_to_edge(self.edge7), 1.0)

    def test_plane_intersection(self):
        v1 = self.edge4.intersects_plane(geom.Plane.XZ)
        v2 = self.edge4.intersects_plane(geom.Plane.Offset(geom.Plane.XZ, dy=1.0))
        v3 = self.edge4.intersects_plane(geom.Plane.Offset(geom.Plane.XZ, dy=1.0), False)
        v4 = self.edge4.intersects_plane(geom.Plane.Offset(geom.Plane.XZ, dy=-5.0))

        self.assertAlmostEqual(v1.x, 5.8333333)
        self.assertEqual(v1.y, 0.0)
        self.assertEqual(v2.x, 6.0)
        self.assertEqual(v2.y, 1.0)
        self.assertIsNone(v3)
        self.assertEqual(v4.x, 5.0)
        self.assertEqual(v4.y, -5.0)

class PlaneTest(unittest.TestCase):
    def test_offset(self):
        xy_plus_ten = geom.Plane.Offset(geom.Plane.XY, dz=10.0)

        self.assertEqual(xy_plus_ten.normal, geom.Vector(0.0, 0.0, 1.0))
        self.assertEqual(xy_plus_ten.point, geom.Vertex(0.0, 0.0, 10.0))

    def test_from_three_points(self):
        pass

    def test_distance_to_point(self):
        self.assertEqual(geom.Plane.XZ.distance_to_point(geom.Vertex(5.0, 2.0, 0.0)), 2.0)
        self.assertEqual(geom.Plane.XZ.distance_to_point(geom.Vertex(-5.0, 3.0, 20.0)), 3.0)
        self.assertEqual(geom.Plane.Offset(geom.Plane.XZ, dy=1.0).distance_to_point(geom.Vertex(-5.0, 3.0, 20.0)), 2.0)

    def test_closest_point(self):
        vc = geom.Plane.XZ.closest_point(geom.Vertex(5.0, 2.0, -1.0))

        self.assertEqual(vc, geom.Vertex(5.0, 0.0, -1.0))

    def test_project_edge(self):
        l1 = geom.Edge(geom.Vertex(-2.0, 2.0, 0.0), geom.Vertex(3.0, 1.0, 0.5))
        l2 = geom.Plane.XZ.project_edge(l1)

        self.assertEqual(l2.v1, geom.Vertex(-2.0, 0.0, 0.0))
        self.assertEqual(l2.v2, geom.Vertex(3.0, 0.0, 0.5))

    def test_vector_angle(self):
        xy_angle = lambda v: geom.Plane.XY.vector_angle(v)

        self.assertAlmostEqual(0.5 * math.pi, xy_angle(geom.Vector(0., 0., 1.)))
        self.assertAlmostEqual(0., xy_angle(geom.Vector(1., 0., 0.)))
        self.assertAlmostEqual(0., xy_angle(geom.Vector(1., 1., 0.)))
        self.assertAlmostEqual(0.25 * math.pi, xy_angle(geom.Vector(1., 0., 1.)))
        self.assertAlmostEqual(0.25 * math.pi, xy_angle(geom.Vector(0., -1., 1.)))

class CylinderTest(unittest.TestCase):
    def setUp(self):
        self.cyl1 = geom.Cylinder(geom.Vertex(0.0, 0.0, 0.0), 1.0, 10.0,
                                  geom.Vector.UnitVector(1.0, 0.0, 0.0))
        self.cyl2 = geom.Cylinder(geom.Vertex(0.0, 1.0, -0.3), 0.5, 5.0,
                                  geom.Vector.UnitVector(1.0, -1.0, 0.0))
        self.cyl3 = geom.Cylinder(geom.Vertex(0.0, -1.0, -1.25), 0.5, 5.0,
                                  geom.Vector.UnitVector(1.0, 1.0, 0.0))
        self.cyl4 = geom.Cylinder(geom.Vertex(0.0, -1.0, -1.51), 0.5, 5.0,
                                  geom.Vector.UnitVector(1.0, 1.0, 0.0))

    def test_volume(self):
        self.assertAlmostEqual(self.cyl1.volume(), 31.4159265)
        self.assertAlmostEqual(self.cyl2.volume(), 3.9269908)

    def test_intersects(self):
        self.assertTrue(self.cyl1.intersects(self.cyl2))
        self.assertTrue(self.cyl2.intersects(self.cyl1))

        self.assertTrue(self.cyl1.intersects(self.cyl3))
        self.assertFalse(self.cyl1.intersects(self.cyl4))
        self.assertTrue(self.cyl2.intersects(self.cyl3))

    def test_discretization(self):
        V = 0.0
        for x in self.cyl1.discretize():
            V += x[1]

        self.assertAlmostEqual(V, self.cyl1.volume())

class CapsuleTest(unittest.TestCase):
    def setUp(self):
        self.caps1 = geom.Capsule(geom.Vertex(0., 0., 0.), 1., 10., geom.Vector(1., 0., 0.))
        self.caps2 = geom.Capsule(geom.Vertex(0., 0., 0.), 1., 10., geom.Vector(1., 1., 1.))

    def test_intersects_plane(self):
        self.assertTrue(self.caps1.intersects_plane(geom.Plane.XZ))
        self.assertTrue(self.caps2.intersects_plane(geom.Plane.XZ))

        self.assertTrue(self.caps1.intersects_plane(geom.Plane.Offset(geom.Plane.XZ, dy=1.0)))
        self.assertFalse(self.caps1.intersects_plane(geom.Plane.Offset(geom.Plane.XZ, dy=1.1)))

        self.assertTrue(self.caps1.intersects_plane(geom.Plane.Offset(geom.Plane.YZ, dx=6.0)))
        self.assertFalse(self.caps1.intersects_plane(geom.Plane.Offset(geom.Plane.YZ, dx=6.1)))

class CuboidTest(unittest.TestCase):
    def setUp(self):
        self.cub1 = geom.Cuboid(geom.Vertex(5.0, 2.5, 1.0), 10.0, 5.0, 2.0)

    def test_volume(self):
        self.assertEqual(self.cub1.volume(), 10.0 * 5.0 * 2.0)

    def test_cylinder_intersect(self):
        cyl1 = geom.Cylinder(geom.Vertex(0.0, 2.5, 1.0), 0.5, 2.0)
        cyl2 = geom.Cylinder(geom.Vertex(5.0, 2.5, 1.0), 0.5, 25.0, geom.Vector(0.0, 1.0, 0.0))

        vol_ratio_1 = self.cub1.volume_intersect(cyl1)
        vol_ratio_2 = self.cub1.volume_intersect(cyl2)

        self.assertAlmostEqual(vol_ratio_1, 0.5 * cyl1.volume())
        self.assertAlmostEqual(vol_ratio_2, 0.2 * cyl2.volume())
