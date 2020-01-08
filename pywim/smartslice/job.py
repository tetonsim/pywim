import enum

from itertools import combinations

from .. import chop, fea, am
from .. import Meta, WimObject, WimList, WimTuple, WimIgnore

from . import  opt, val

def get_config_attribute(configs, attr_name):
    is_aux = not hasattr(configs[0], attr_name)

    if is_aux:
        for c in configs:
            if attr_name in c.auxiliary:
                return c.auxiliary[attr_name]
    else:
        for c in configs:
            attr_val = getattr(c, attr_name)

            if attr_val is am.InfillType.unknown:
                attr_val = None

            elif (attr_name is "skin_orientations") and (len(attr_val) == 0):
                attr_val = None

            if attr_val:
                return attr_val

    return None

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

    def top_config(self, mesh_config):
        global_config = self.chop.slicer.print_config

        if len(self.chop.slicer.printer.extruders) > 0:
            extruder_config = self.chop.slicer.printer.extruders[0].print_config

        else:
            extruder_config = global_config

        top_config = am.Config()

        configs = (mesh_config, extruder_config, global_config)
        
        for p in val.checked_print_parameters:
            is_aux = not hasattr(top_config, p) and (p not in ['infill.pattern', 'infill.density', 'infill.orientation'])

            if is_aux:
                top_config.auxiliary[p] = get_config_attribute(configs, p)

            else:
                if p in ['infill.pattern', 'infill.density', 'infill.orientation']:
                    s = p.split(".")
                    infill_configs = (mesh_config.infill, extruder_config.infill, global_config.infill)
                    setattr(top_config.infill, s[1], get_config_attribute(infill_configs, s[1]))

                else:
                    setattr(top_config, p, get_config_attribute(configs, p))

        return top_config

    def _validate_requirements(self):
        '''
        Check the auxiliary print settings for validity.
        '''
        errors = []

        for mesh in self.chop.meshes:
        
            for key,value in val.specific_reqs.items():

                if mesh.print_config.auxiliary[key] is not value[0]:
                    errors.append( val.InvalidPrintSetting(mesh, value[1], mesh.print_config.auxiliary[key], value[0]) )

            for key,value in val.comparative_reqs.items():

                if mesh.print_config.auxiliary[key] is not getattr(mesh.print_config, value[0]):
                    errors.append( val.IncompatiblePrintSetting(mesh, value[1], mesh.print_config.auxiliary[key], 
                                                                value[2], getattr(mesh.print_config, value[0])) )

            # Infill Density Bounds
            if not ( val.infill_reqs[0][1] <= getattr(mesh.print_config.infill, val.infill_reqs[0][0]) <= val.infill_reqs[0][2] ):
                errors.append( val.OutOfBoundsPrintSetting(mesh, val.infill_reqs[0][3], val.infill_reqs[0][1], val.infill_reqs[0][2]) )

            # Infill Pattern
            if getattr(mesh.print_config.infill, val.infill_reqs[1][0]) not in val.infill_reqs[1][1]:
                errors.append( val.UnsupportedPrintOptionSetting(mesh, val.infill_reqs[1][2], val.infill_reqs[1][1]) )

            # Infill Line Directions
            if not (val.infill_reqs[2][1] <= len(mesh.print_config.auxiliary[val.infill_reqs[2][0]]) <= val.infill_reqs[2][2]):
                errors.append( val.OutOfBoundsPrintSetting(mesh, val.infill_reqs[2][3], val.infill_reqs[2][1], val.infill_reqs[2][2]) )

        return errors

    def _validate_compatibility(self):
        '''
        Check for print setting compatibility between meshes. Currently, only layer height and layer width.
        '''
        errors = []

        for key,value in val.compatibility_parameters.items():

            for pair in list(combinations(self.chop.meshes, 2)):

                if getattr(pair[0].print_config, key) != getattr(pair[1].print_config, key):
                    
                    errors.append( val.MismatchedPrintSetting(pair[0], pair[1], value) )

        return errors

    def validate(self):
        '''
        Function for validating the print configs for use in smartslice validation.
        '''
        # First, we need to adjust each mesh's print config to contain all relevant information.
        for mesh in self.chop.meshes:
            mesh.print_config = self.top_config(mesh.print_config)

        comp_errors = self._validate_compatibility() if (len(self.chop.meshes) > 1) else []

        req_errors = self._validate_requirements()

        return comp_errors + req_errors
