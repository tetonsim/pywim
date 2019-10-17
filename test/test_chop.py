import unittest
import numpy as np

import threemf
import pywim

class MeshTest(unittest.TestCase):
    def test_mesh_transform(self):
        # The chop Mesh object has to use the __from_dict__ and __to_dict__
        # method overrides, so this is to test those are working correctly

        # This is not a valid transformation matrix, just using
        # it to test the individual components get restored correctly
        T = np.array(
            [
                [1., 2., 3., 4.],
                [5., 6., 7., 8.],
                [9., 10., 11., 12.],
                [13., 14., 15., 16.],
            ]
        )

        mesh = pywim.chop.mesh.Mesh()
        mesh.transform = T
        mesh.type = pywim.chop.mesh.MeshType.infill
        mesh.materials.extrusion = 'mat-1'
        mesh.materials.infill = 'mat-2'

        d = mesh.to_dict()

        mesh2 = pywim.chop.mesh.Mesh.from_dict(d)

        self.assertTrue(np.array_equal(mesh2.transform, T))
        self.assertEqual(mesh2.type, pywim.chop.mesh.MeshType.infill)
        self.assertEqual(mesh2.materials.extrusion, 'mat-1')
        self.assertEqual(mesh2.materials.infill, 'mat-2')
