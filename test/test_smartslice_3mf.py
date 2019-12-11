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
        job : pwyim.smartslice.job.Job = asset.content

        ss.assets.append(asset)

        tmf.extensions.append(ss)

        return tmf

    def _write_3mf_bytes(self, tmf):
        tmf_bytes = io.BytesIO()

        tmf_writer = threemf.io.Writer()
        tmf_writer.write(tmf, tmf_bytes)

        with open('/home/brady/tmp/test.3mf', 'wb') as f:
            tmf_writer.write(tmf, f)
        
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

        job : pywim.smartslice.job.Job = asset.content
        
        self.assertTrue(isinstance(job, pywim.smartslice.job.Job))
        self.assertEqual(len(job.chop.meshes), 1)

        mesh : pywim.chop.mesh.Mesh = job.chop.meshes[0]

        np.testing.assert_array_equal(mesh.transform, np.identity(4))

        self.assertEqual(len(mesh.triangles), 12)
        self.assertEqual(len(mesh.vertices), 36)
