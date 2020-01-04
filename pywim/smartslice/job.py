import enum

from .. import chop, fea, am
from .. import Meta, WimObject, WimList, WimTuple, WimIgnore

from . import  opt

class JobType(enum.Enum):
    validation = 1
    optimization = 2

class Job(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.type = JobType.validation
        self.chop = chop.model.Model()
        self.bulk = fea.model.Material()
        self.optimization = opt.Optimization()

    def validate(self):
        '''
        Function for validating the print configs for use in smartslice validation.
        '''

        global_config = self.chop.slicer.print_config

        extruder_config = self.chop.slicer.printer.extruders[0].print_config

        mod_meshes_config = []

        for i in range(len(self.chop.meshes)):

            if self.chop.meshes[i].type is chop.mesh.MeshType.normal:
                normal_mesh_config = self.chop.meshes[i].print_config
            else:
                mod_meshes_config.append(self.chop.meshes[i].print_config)

        # Set the layer height to be used throughout.
        if normal_mesh_config.layer_height:
            layer_height = normal_mesh_config.layer_height

        elif extruder_config.layer_height:
            layer_height = extruder_config.layer_height

        else:
            layer_height = global_config.layer_height

        # Set the layer width to be used throughout.
        if normal_mesh_config.layer_width:
            layer_width = normal_mesh_config.layer_width

        elif extruder_config.layer_width:
            layer_width = extruder_config.layer_width

        else:
            layer_width = global_config.layer_width

        # Dictionary containing the keys and required values.
        reqs = {"extruders_enabled_count": 1,
                "layer_height_0": layer_height,
                "infill_line_width": layer_width,
                "skin_line_width": layer_width,
                "wall_line_width_0": layer_width,
                "wall_line_width_x": layer_width,
                "wall_line_width": layer_width,
                "initial_layer_line_width_factor": 100,
                "top_bottom_pattern": "lines",
                "top_bottom_pattern_0": "lines",
                "infill_sparse_thickness": layer_height,
                "gradual_infill_steps": 0,
                "mold_enabled": false,
                "magic_mesh_surface_mode": "normal",
                "magic_spiralize": false,
                "spaghetti_infill_enabled": false,
                "magic_fuzzy_skin_enabled": false,
                "wireframe_enabled": false,
                "adaptive_layer_height_enabled": false
        }

        for key,value in reqs:

            if global_config.auxiliary[key] is not value:
                pass # pass error for this

            if extruder_config.auxiliary[key] is not value:
                pass # pass error for this

            if normal_mesh_config.auxiliary[key] is not value:
                pass # pass error for this

            for c in mod_meshes_config:

                if c.auxiliary[key] is not value:
                    pass # pass error for this

        # Infill requirements must be handled separately.

        # Set the infill density min and max
        infill_density_min = 20
        infill_density_max = 100

        # Infill Density Min
        if global_config.infill.density < infill_density_min:
            pass # pass error for this

        if extruder_config.infill.density < infill_density_min:
            pass # pass error for this

        if normal_mesh_config.infill.density < infill_density_min:
            pass # pass error for this
        
        for c in mod_meshes_config:

                if c.infill.density < infill_density_min:
                    pass # pass error for this

        # Infill Density Max
        if global_config.infill.density > infill_density_max:
            pass # pass error for this

        if extruder_config.infill.density > infill_density_max:
            pass # pass error for this

        if normal_mesh_config.infill.density > infill_density_max:
            pass # pass error for this
        
        for c in mod_meshes_config:

                if c.infill.density > infill_density_max:
                    pass # pass error for this

        # Infill Pattern
        if (global_config.infill.pattern is not am.InfillType.grid) or (global_config.infill.pattern is not am.InfillType.triangle):
            pass # pass error for this

        if (extruder_config.infill.pattern is not am.InfillType.grid) or (extruder_config.infill.pattern is not am.InfillType.triangle):
            pass # pass error for this

        if (normal_mesh_config.infill.pattern is not am.InfillType.grid) or (normal_mesh_config.infill.pattern is not am.InfillType.triangle):
            pass # pass error for this
        
        for c in mod_meshes_config:

                if (c.infill.pattern is not am.InfillType.grid) or (c.infill.pattern is not am.InfillType.triangle):
                    pass # pass error for this

        # Infill Line Directions
        if len(global_config.auxiliary["infill_angles"]) > 1:
            pass # pass error for this

        if len(extruder_config.auxiliary["infill_angles"]) > 1:
            pass # pass error for this

        if len(normal_mesh_config.auxiliary["infill_angles"]) > 1:
            pass # pass error for this
        
        for c in mod_meshes_config:

                if len(c.auxiliary["infill_angles"]) > 1:
                    pass # pass error for this