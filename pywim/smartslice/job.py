import enum

from itertools import combinations

from .. import chop, fea, am
from .. import Meta, WimObject, WimList, WimTuple, WimIgnore

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
        
        for p in val.NECESSARY_PRINT_PARAMETERS:
            top_config = set_config_attribute(top_config, configs, p)

        return top_config

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
        # First, we need to adjust each mesh's print config to contain all relevant information.
        for mesh in self.chop.meshes:
            mesh.print_config = self.top_config(mesh.print_config)

        comp_errors = self._validate_compatibility() if (len(self.chop.meshes) > 1) else []

        req_errors = self._validate_requirements()

        return comp_errors + req_errors
