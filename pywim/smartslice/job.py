import enum

from itertools import combinations

from .. import chop, fea, am
from .. import Meta, WimObject, WimList

from . import  opt, val

def set_config_attribute(top_config, configs, attr_name):
    lev_names = []
    sub_lev_names = []
    sub_levs = []

    # Determine if attr_name is part of a sub-attribute.
    if '.' in attr_name:
        lev_names = attr_name.split('.')
        attr_name = lev_names[-1]
        sub_lev_names = lev_names[0:len(lev_names) - 1]

        # Descend each config to the correct level for the new attr_name.
        new_configs = []

        for c in configs:
            for l in sub_lev_names:
                c = getattr(c, l)

            new_configs.append(c)

        configs = new_configs

        cur_lev = top_config

        for l in sub_lev_names:
            cur_lev = getattr(top_config, l)
            sub_levs.append( cur_lev )

    is_aux = not hasattr(configs[0], attr_name)

    if is_aux:
        for c in configs:
            if attr_name in c.auxiliary:
                top_config.auxiliary[attr_name] = c.auxiliary[attr_name]

                return top_config
    else:
        for c in configs:
            attr_val = getattr(c, attr_name)

            if attr_val == am.InfillType.unknown:
                attr_val = None

            elif isinstance(attr_val, list) and (len(attr_val) == 0):
                attr_val = None

            if attr_val:
                for i in range(1, len(sub_levs) + 1):
                    setattr(sub_levs[-i], lev_names[-i], attr_val)
                    attr_name = lev_names[-(i+1)]
                    attr_val = sub_levs[-i]

                setattr(top_config, attr_name, attr_val)

                return top_config

    return top_config

class JobType(enum.Enum):
    validation = 1
    optimization = 2

class Extruder(WimObject):
    def __init__(self, number=0):
        self.number = number

        # list of names of materials that are available for use in this extruder
        self.usable_materials = WimList(str)

class Job(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.type = JobType.validation
        self.chop = chop.model.Model()
        self.bulk = WimList(fea.model.Material)
        self.extruders = WimList(Extruder)
        self.optimization = opt.Optimization()

    @property
    def materials(self):
        '''Alias for bulk'''
        return self.bulk


    def top_config(self, mesh_config):
        global_config = self.chop.slicer.print_config

        if len(self.chop.slicer.printer.extruders) == 0:
            configs = (mesh_config, global_config)

        else:
            extruder_config = self.chop.slicer.printer.extruders[0].print_config
            configs = (mesh_config, extruder_config, global_config)

        top_config = am.Config()

        for p in val.NECESSARY_PRINT_PARAMETERS:
            top_config = set_config_attribute(top_config, configs, p)

        return top_config

    def _validate_steps(self):
        '''
        Check the step definitions
        '''
        errors = []

        if (self.chop.steps.is_empty()):
            errors.append(val.InvalidSetup('No loads or anchors have been defined', 
                'Define at least one load and boundary condition'))

        for step in self.chop.steps:
            if step.boundary_conditions.is_empty():
                errors.append(val.InvalidSetup('No anchors have been defined for step ' + step.name, 
                    'Define at least one anchor for the step'))

            for bc in step.boundary_conditions:
                if (bc.face.is_empty()):
                    errors.append(val.InvalidSetup('No faces have been selected for anchor ' + bc.name, 
                        'Select a face to apply the anchor'))

            if step.loads.is_empty():
                errors.append(val.InvalidSetup('No loads have been defined for step ' + step.name, 
                    'Define at least one load for the step'))

            for load in step.loads:
                if (load.face.is_empty()):
                    errors.append(val.InvalidSetup('No faces have been selected for load ' + load.name, 
                        'Select a face to apply the load'))

            
        return errors

    def _validate_requirements(self):
        '''
        Check the auxiliary print settings for validity.
        '''
        errors = []

        for mesh in self.chop.meshes:

            for req in val.REQUIREMENTS:
                req_error = req.check_error(mesh)

                if req_error:
                    errors.append(req_error)

        return errors

    def _validate_compatibility(self):
        '''
        Check for print setting compatibility between meshes. Currently, only layer height and layer width.
        '''
        errors = []

        for req in val.CONFIG_MATCHING:

            for pair in list(combinations(self.chop.meshes, 2)):

                req_error = req.check_error(pair[0], pair[1])

                if req_error:
                    errors.append(req_error)

        return errors

    def validate(self):
        '''
        Function for validating the print configs for use in smartslice validation.
        '''
        mesh_errors = []
        if (self.chop.meshes.is_empty()):
            mesh_errors.append(val.InvalidSetup('No meshes have been defined for this job', 
                'Define at least one mesh to be used in the job'))

        step_errors = self._validate_steps()

        return mesh_errors + step_errors

        # # Adjust each mesh's print config to contain all relevant information.
        # for mesh in self.chop.meshes:
        #     mesh.print_config = self.top_config(mesh.print_config)

        # comp_errors = self._validate_compatibility() if (len(self.chop.meshes) > 1) else []

        # req_errors = self._validate_requirements()

        # return mesh_errors + step_errors + comp_errors + req_errors

    