import unittest
import numpy as np

import threemf
import pywim

specific_reqs = {
    'extruders_enabled_count': [1, 'Number of Extruders That Are Enabled'],
    'initial_layer_line_width_factor': [100, 'Initial Layer Line Width'],
    'top_bottom_pattern': ['lines', 'Top/Bottom Pattern'],
    'top_bottom_pattern_0': ['lines', 'Bottom Pattern Initial Layer'],
    'gradual_infill_steps': [0, 'Gradual Infill Steps'],
    'mold_enabled': ['false', 'Mold'],
    'magic_mesh_surface_mode': ['normal', 'Surface Mode'],
    'magic_spiralize': ['false', 'Spiralize Outer Contour'],
    'spaghetti_infill_enabled': ['false', 'Spaghetti Infill'],
    'magic_fuzzy_skin_enabled': ['false', 'Fuzzy Skin'],
    'wireframe_enabled': ['false', 'Wire Printing'],
    'adaptive_layer_height_enabled': ['false', 'Use Adaptive Layers']
}

comparative_reqs = {
    'layer_height_0': ['layer_height', 'Initial Layer Height', 'Layer Height'],
    'infill_line_width': ['layer_width', 'Infill Line Width', 'Layer Width'],
    'skin_line_width': ['layer_width', 'Top/Bottom Line Width', 'Layer Width'],
    'wall_line_width_0': ['layer_width', 'Outer Wall Line Width', 'Layer Width'],
    'wall_line_width_x': ['layer_width', 'Inner Wall(s) Line Width', 'Layer Width'],
    'wall_line_width': ['layer_width', 'Wall Line Width', 'Layer Width'],
    'infill_sparse_thickness': ['layer_height', 'Infill Layer Thickness', 'Layer Height'],
}

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
    def test_set_config_attribute(self):
        c1 = pywim.am.Config()
        c2 = pywim.am.Config().Defaults()

        c1.layer_width = 0.5
        c1.infill.density = 57
        c1.auxiliary['mold_enabled'] = True

        top_config = pywim.am.Config()

        self.assertEqual(pywim.smartslice.job.set_config_attribute( top_config, (c1, c2), 'layer_width').layer_width, 0.5 )
        self.assertEqual(pywim.smartslice.job.set_config_attribute( top_config, (c1, c2), 'infill.density').infill.density, 57 )
        self.assertEqual(pywim.smartslice.job.set_config_attribute( top_config, (c1, c2), 'mold_enabled').auxiliary['mold_enabled'], True )

    def test_top_config(self):
        c0 = pywim.am.Config()
        c0.layer_width = 0.6
        c0.auxiliary['mold_enabled'] = True
        c0.infill.density = 87

        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.bottom_layers = 1
        c1.infill.pattern = pywim.am.InfillType.triangle

        c2 = pywim.am.Config().Defaults()
        c2.auxiliary['mold_enabled'] = False
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
        self.assertEqual(top_config.auxiliary['mold_enabled'], True)
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

        for key,value in specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

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

        for key,value in specific_reqs.items():

            c2.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

            c2.auxiliary[key] = getattr(c1, value[0])

        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job._validate_requirements(check_strict=True, check_optional=True)

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

        for key,value in specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

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

        for key,value in specific_reqs.items():

            c2.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

            c2.auxiliary[key] = getattr(c1, value[0])

        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job._validate_requirements(check_strict=True, check_optional=True)

        self.assertEqual( len(errors), 3)

        error_names = set([errors[0].setting_name, errors[1].setting_name, errors[2].setting_name])

        results_names = set(['Infill Density', 'Infill Pattern', 'Number of Infill Line Directions'])

        self.assertEqual(error_names, results_names)

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

        for key,value in specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])

        c1.auxiliary['extruders_enabled_count'] = 0
        c1.auxiliary['skin_line_width'] = 0.8

        mesh1.print_config = c1

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)

        errors = job._validate_requirements(check_strict=True, check_optional=True)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].setting_name, 'Top/Bottom Line Width')

    def test_validate_reqs_4(self):
        mesh1 = pywim.chop.mesh.Mesh()
        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.layer_width = 0.6
        c1.bottom_layers = 1
        c1.infill.density = 20
        c1.infill.pattern = pywim.am.InfillType.triangle
        c1.infill.orientation = 0.0
        c1.auxiliary['infill_angles'] = []

        for key,value in specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])

        c1.auxiliary['extruders_enabled_count'] = 0
        c1.auxiliary['skin_line_width'] = 0.8

        mesh1.print_config = c1

        job = pywim.smartslice.job.Job()
        job.chop.meshes.append(mesh1)

        errors = job._validate_requirements(check_strict=True, check_optional=False)

        self.assertEqual(len(errors), 0)

    def test_validate(self):
        mesh1 = pywim.chop.mesh.Mesh('mesh1')
        c1 = pywim.am.Config()
        c1.layer_height = 0.4
        c1.layer_width = 0.6
        c1.bottom_layers = 1
        c1.infill.density = 10
        c1.infill.pattern = pywim.am.InfillType.triangle
        c1.infill.orientation = 0.0
        c1.auxiliary['infill_angles'] = [0, 1]

        for key,value in specific_reqs.items():

            c1.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

            c1.auxiliary[key] = getattr(c1, value[0])

        c1.auxiliary['extruders_enabled_count'] = 0
        c1.auxiliary['skin_line_width'] = 0.8

        mesh1.print_config = c1

        mesh2 = pywim.chop.mesh.Mesh('mesh2')
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

        for key,value in specific_reqs.items():

            c2.auxiliary[key] = value[0]

        for key,value in comparative_reqs.items():

            c2.auxiliary[key] = getattr(c1, value[0])

        mesh2.print_config = c2

        job = pywim.smartslice.job.Job()
        job.chop.slicer.print_config = c2
        job.chop.slicer.printer.extruders.append(pywim.chop.machine.Extruder())
        job.chop.slicer.printer.extruders[0].print_config = c2
        job.chop.meshes.append(mesh1)
        job.chop.meshes.append(mesh2)

        errors = job.validate(check_step=True, check_compatibility=True, check_strict=True, check_optional=False)

        self.assertEqual( len(errors), 4)

        #error_names = set([errors[0].setting_name, errors[1].setting_name, errors[2].setting_name, errors[3].setting_name, errors[4].setting_name])
        error_names = set([
            e.setting_name if hasattr(e, 'setting_name') else e.error() for e in errors
        ])

        results_names = set(['No loads or anchors have been defined', 'Infill Density', 'Infill Pattern', 'Number of Infill Line Directions'])

        self.assertEqual(error_names, results_names)
