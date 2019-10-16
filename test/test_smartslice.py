import unittest
import numpy as np

import threemf
import pywim

class MeshTest(unittest.TestCase):
    def test_mesh_transform(self):
        # This tests that the transformation matrix gets
        # serialized and de-serialized correctly

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

        mesh = pywim.chop.Mesh()
        mesh.transform = T

        d = mesh.to_dict()

        mesh2 = pywim.chop.Mesh.from_dict(d)

        self.assertTrue(np.array_equal(mesh2.transform, T))
