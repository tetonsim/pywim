import unittest
import io
import numpy as np

import pywim
import threemf

from . import stl_loader

class SmartSlice3MFTest(unittest.TestCase):
    def _create_3mf(self):
        tmf = threemf.ThreeMF()

        mdl = tmf.default_model

        mesh = stl_loader.load_from_file('cube.stl')
        obj = mdl.object_from_stl(mesh)
        mdl.build.add_item(obj)

        ss = pywim.smartslice.ThreeMFExtension()
        asset = ss.make_asset('job.json')
        job = asset.content

        ss.assets.append(asset)

        tmf.extensions.append(ss)

        return tmf

    def _write_3mf_bytes(self, tmf):
        tmf_bytes = io.BytesIO()

        tmf_writer = threemf.io.Writer()
        tmf_writer.write(tmf, tmf_bytes)

        return tmf_bytes

    def _read_3mf_bytes(self, tmf_bytes) -> threemf.ThreeMF:
        tmf = threemf.ThreeMF()
        rdr = threemf.io.Reader()

        rdr.register_extension(pywim.smartslice.ThreeMFExtension)

        rdr.read(tmf, tmf_bytes)

        return tmf

    def test_basic_3mf(self):
        tmf = self._create_3mf()
        tmf_bytes = self._write_3mf_bytes(tmf)
        tmf = self._read_3mf_bytes(tmf_bytes)

        # Check that the smart slice job was created and it contains the mesh
        self.assertEqual(len(tmf.extensions), 1)

        ext = tmf.extensions[0]

        self.assertTrue(isinstance(ext, pywim.smartslice.ThreeMFExtension))
        self.assertEqual(len(ext.assets), 1)

        asset = ext.assets[0]

        self.assertTrue(isinstance(asset, pywim.smartslice.JobThreeMFAsset))

        job = asset.content

        self.assertTrue(isinstance(job, pywim.smartslice.job.Job))
        self.assertEqual(len(job.chop.meshes), 1)

        mesh = job.chop.meshes[0]

        np.testing.assert_array_equal(mesh.transform, np.identity(4))

        self.assertEqual(len(mesh.triangles), 12)
        self.assertEqual(len(mesh.vertices), 36)

    def test_mod_mesh_3mf(self):
        tmf = self._create_3mf()

        # Add a modifier mesh before we write and read the 3MF
        mdl = tmf.default_model
        mesh = stl_loader.load_from_file('cube.stl')
        obj = mdl.object_from_stl(mesh)

        obj.add_meta_data_cura('infill_mesh', True)
        obj.add_meta_data_cura('infill_sparse_density', 50)
        obj.add_meta_data_cura('infill_pattern', pywim.am.InfillType.grid.name)
        obj.add_meta_data_cura('infill_angles', '[ 10 ]')
        obj.add_meta_data_cura('wall_line_count', 4)
        obj.add_meta_data_cura('bottom_layers', 8)
        obj.add_meta_data_cura('top_layers', 9)
        obj.add_meta_data_cura('skin_angles', [-10, 10])

        T = np.identity(4)
        T[0,3] = 50.
        T[1,3] = 50.

        mdl.build.add_item(obj, T)

        # Write and read the 3MF back in
        tmf_bytes = self._write_3mf_bytes(tmf)
        tmf = self._read_3mf_bytes(tmf_bytes)

        job = tmf.extensions[0].assets[0].content

        self.assertEqual(len(job.chop.meshes), 2)

        m0 = job.chop.meshes[0]
        m1 = job.chop.meshes[1]

        self.assertEqual(m0.type, pywim.chop.mesh.MeshType.normal)
        self.assertEqual(m1.type, pywim.chop.mesh.MeshType.infill)

        self.assertEqual(m1.print_config.walls, 4)
        self.assertEqual(m1.print_config.bottom_layers, 8)
        self.assertEqual(m1.print_config.top_layers, 9)
        self.assertEqual(m1.print_config.skin_orientations, [-10, 10])
        self.assertEqual(m1.print_config.infill.density, 50)
        self.assertEqual(m1.print_config.infill.pattern, pywim.am.InfillType.grid)
        self.assertEqual(m1.print_config.infill.orientation, 10)

