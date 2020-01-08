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

class JobValidateTest(unittest.TestCase):
    def test_get_config_attribute(self):
        c1 = pywim.am.Config()
        c2 = pywim.am.Config().Defaults()

        c1.layer_width = 0.5
        c1.auxiliary["mold_enabled"] = True

        self.assertEqual(pywim.smartslice.job.get_config_attribute( (c1, c2), 'layer_width'), 0.5 )
        self.assertEqual(pywim.smartslice.job.get_config_attribute( (c1, c2), 'mold_enabled'), True )
        self.assertEqual(pywim.smartslice.job.get_config_attribute( (c1, c2), 'extruders_enabled_count'), None )

    def test_top_config(self):
        c0 = pywim.am.Config()
        c0.layer_width = 0.6
        c0.auxiliary["mold_enabled"] = True
        c0.infill.density = 87

        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.bottom_layers = 1
        c1.infill.pattern = pywim.am.InfillType.triangle

        c2 = pywim.am.Config().Defaults()
        c2.auxiliary["mold_enabled"] = False
        c2.auxiliary['extruders_enabled_count'] = 2

        job = pywim.smartslice.job.Job()
        job.chop.slicer.print_config = c2
        job.chop.slicer.printer.extruders.append(pywim.chop.machine.Extruder())
        job.chop.slicer.printer.extruders[0].print_config = c1

        top_config = job.top_config(c0)

        self.assertEqual(top_config.layer_width, 0.6)
        self.assertEqual(top_config.layer_height, 0.4)
        self.assertEqual(top_config.walls, 2)
        self.assertEqual(top_config.bottom_layers, 1)
        self.assertEqual(top_config.top_layers, 6)
        self.assertEqual(top_config.infill.density, 87)
        self.assertEqual(top_config.infill.pattern, pywim.am.InfillType.triangle)
        self.assertEqual(top_config.auxiliary["mold_enabled"], True)
        self.assertEqual(top_config.auxiliary['extruders_enabled_count'], 2)

    def test_validate_compatability_1(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.5
        c1.layer_width = 0.3
        mesh1.print_config = c1

        mesh2 = pywim.chop.mesh.Mesh()
        c2 = pywim.am.Config()
        c2.layer_height = 0.4
        c2.layer_width = 0.3
        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job._validate_compatibility()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].setting_name, 'Layer Height')

    def test_validate_compatability_2(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.5
        c1.layer_width = 0.4
        mesh1.print_config = c1

        mesh2 = pywim.chop.mesh.Mesh()
        c2 = pywim.am.Config()
        c2.layer_height = 0.5
        c2.layer_width = 0.3
        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job._validate_compatibility()

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].setting_name, 'Line Width')

    def test_validate_reqs_1(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.layer_width = 0.6
        c1.bottom_layers = 1
        c1.infill.density = 20
        c1.infill.pattern = pywim.am.InfillType.triangle
        c1.infill.orientation = 0.0
        c1.auxiliary['infill_angles'] = []

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])
        
        mesh1.print_config = c1

        mesh2 = pywim.chop.mesh.Mesh()
        c2 = pywim.am.Config()
        c2.layer_height = 0.4
        c2.layer_width = 0.6
        c2.bottom_layers = 1
        c2.infill.density = 30
        c2.infill.pattern = pywim.am.InfillType.triangle
        c2.infill.orientation = 0.0
        c2.auxiliary['infill_angles'] = []

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c2.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c2.auxiliary[key] = getattr(c1, value[0])
        
        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job._validate_requirements()

        self.assertEqual( errors, [])

    def test_validate_reqs_2(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.layer_width = 0.6
        c1.bottom_layers = 1
        c1.infill.density = 10
        c1.infill.pattern = pywim.am.InfillType.triangle
        c1.infill.orientation = 0.0
        c1.auxiliary['infill_angles'] = [0, 1]

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])
        
        mesh1.print_config = c1

        mesh2 = pywim.chop.mesh.Mesh()
        c2 = pywim.am.Config()
        c2.layer_height = 0.4
        c2.layer_width = 0.6
        c2.bottom_layers = 1
        c2.infill.density = 30
        c2.infill.pattern = pywim.am.InfillType.cubic
        c2.infill.orientation = 0.0
        c2.auxiliary['infill_angles'] = []

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c2.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c2.auxiliary[key] = getattr(c1, value[0])
        
        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job._validate_requirements()

        self.assertEqual( len(errors), 3)
        self.assertEqual(errors[0].setting_name, 'Infill Density')
        self.assertEqual(errors[2].setting_name, 'Infill Pattern')
        self.assertEqual(errors[1].setting_name, 'Infill Line Directions')

    def test_validate_reqs_3(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.layer_width = 0.6
        c1.bottom_layers = 1
        c1.infill.density = 20
        c1.infill.pattern = pywim.am.InfillType.triangle
        c1.infill.orientation = 0.0
        c1.auxiliary['infill_angles'] = []

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])
        
        c1.auxiliary["extruders_enabled_count"] = 0
        c1.auxiliary["skin_line_width"] = 0.8

        mesh1.print_config = c1

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)

        errors = job._validate_requirements()

        self.assertEqual( len(errors), 2)
        self.assertEqual(errors[0].setting_name, "Number of Extruders That Are Enabled")
        self.assertEqual(errors[1].setting_name, "Top/Bottom Line Width")

    def test_validate(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.layer_width = 0.6
        c1.bottom_layers = 1
        c1.infill.density = 10
        c1.infill.pattern = pywim.am.InfillType.triangle
        c1.infill.orientation = 0.0
        c1.auxiliary['infill_angles'] = [0, 1]

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])

        c1.auxiliary["extruders_enabled_count"] = 0
        c1.auxiliary["skin_line_width"] = 0.8
        
        mesh1.print_config = c1

        mesh2 = pywim.chop.mesh.Mesh()
        c2 = pywim.am.Config()
        c2.layer_height = 0.4
        c2.layer_width = 0.6
        c2.walls = 4
        c2.top_layers = 3
        c2.bottom_layers = 1
        c2.infill.density = 30
        c2.infill.pattern = pywim.am.InfillType.cubic
        c2.infill.orientation = 0.0
        c2.auxiliary['infill_angles'] = []

        for key,value in pywim.smartslice.job.val.specific_reqs.items():

            c2.auxiliary[key] = value[0]

        for key,value in pywim.smartslice.job.val.comparative_reqs.items():

            c2.auxiliary[key] = getattr(c1, value[0])
        
        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.slicer.print_config = c2
        job.chop.slicer.printer.extruders.append(pywim.chop.machine.Extruder())
        job.chop.slicer.printer.extruders[0].print_config = c2
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job.validate()

        self.assertEqual( len(errors), 5)
        self.assertEqual(errors[0].setting_name, "Number of Extruders That Are Enabled")
        self.assertEqual(errors[1].setting_name, "Top/Bottom Line Width")
        self.assertEqual(errors[2].setting_name, 'Infill Density')
        self.assertEqual(errors[4].setting_name, 'Infill Pattern')
        self.assertEqual(errors[3].setting_name, 'Infill Line Directions')