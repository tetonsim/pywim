import copy
import math

from . import WimObject, WimList

class Infill(WimObject):
    def __init__(self):
        self.pattern = 'grid'
        self.density = 50
        self.orientation = 0.0

class Layer(WimObject):
    def __init__(self, orientation=0.0):
        self.orientation = orientation

class Stack(WimObject):
    def __init__(self):
        self.layers = WimList(Layer)

    @property
    def count(self):
        return len(self.layers)

    @classmethod
    def Cycle(cls, count, orientations):
        stack = cls()

        nori = len(orientations)
        if nori == 0:
            nori = 1
            orientations = [0.0]

        i = 0
        l = 0
        while i < max(1, count):
            lay = Layer(orientations[l])
            stack.layers.append( lay )
            
            i += 1
            l += 1

            if l == nori:
                l = 0

        return stack

class Config(WimObject):
    def __init__(self):
        self.layer_width = 0.45
        self.layer_height = 0.2
        self.walls = 2
        self.bottom_layer = Stack.Cycle(6, [45., -45.])
        self.top_layer = Stack.Cycle(6, [45., -45.])
        self.infill = Infill()

    @staticmethod
    def default_overlap(layer_height):
        return layer_height * (1.0 - math.pi / 4.0)

from . import micro, model

class FDMModelFactory:
    class ElementSets:
        def __init__(self, wall : str, bottom_layer : str, top_layer : str, global_infill : str):
            self.wall = wall
            self.bottom_layer = bottom_layer
            self.top_layer = top_layer
            self.global_infill = global_infill
            self.local_infills = { }

        def set_local_infill(self, infill_config : Infill, local_infill_element_set_name : str, element_ids : set):
            self.local_infills[local_infill_element_set_name] = (element_ids, infill_config)

    def __init__(self, model : model.Model, bulk_material : model.Material):
        self.model = model
        self.bulk_material = bulk_material

        self.model.materials.clear()
        self.model.materials.add(self.bulk_material)

        self.model.sections.clear()
        self.model.section_assignments.clear()

    def create(self, config : Config, element_sets : 'FDMModel.ElementSets') -> model.Model:
        # temporary - not supporting local infills at the moment
        if len(element_sets.local_infills) > 0:
            raise NotImplementedError('Unable to modify model for localized infill configurations')

        nmdl = copy.deepcopy(self.model)

        # Setup micromechanics jobs
        layer_mat_name = 'layer'
        layer_job = micro.build.job.ExtrudedLayer(self.bulk_material, config, name=layer_mat_name)

        global_infill_mat_name = 'infill-%f' % config.infill.density
        global_infill_job = micro.build.job.Infill(layer_job, config, name=global_infill_mat_name)

        nmdl.jobs.add(layer_job)
        nmdl.jobs.add(global_infill_job)

        # Create localized infill micromechanics jobs and associated sections
        local_infill_sections = []

        for elset_name, local_infill in element_sets.local_infills.items():
            local_infill_mat_name = 'infill-%f' % local_infill[1].density
            
            local_config = copy.deepcopy(config)
            local_config.infill = local_infill[1]

            local_infill_job = micro.build.job.Infill(layer_job, local_config, name=local_infill_mat_name)

            nmdl.jobs.add(local_infill_job)

            local_infill_sections.append(
                model.FDMInfillSection(f'section-{local_infill_mat_name}', local_infill_mat_name, local_config.infill.orientation)
            )

        # Setup sections
        wall_section = model.FDMWallSection('wall', layer_mat_name, config.walls)
        bottom_layer_section = model.FDMLayerSection('bottom_layer')
        top_layer_section = model.FDMLayerSection('top_layer')

        for l in config.bottom_layer.layers:
            bottom_layer_section.layers.add(
                model.Layer(layer_mat_name, l.orientation, config.layer_height)
            )

        for l in config.top_layer.layers:
            top_layer_section.layers.add(
                model.Layer(layer_mat_name, l.orientation, config.layer_height)
            )

        global_infill_section = model.FDMInfillSection('global-infill', global_infill_mat_name, config.infill.orientation)

        nmdl.sections.extend([
            wall_section, bottom_layer_section, top_layer_section, global_infill_section
        ])

        nmdl.sections.extend(local_infill_sections)

        # Setup section assignments
        nmdl.section_assignments.extend([
            model.SectionAssignment(wall_section.name, wall_section.name, element_sets.wall),
            model.SectionAssignment(bottom_layer_section.name, bottom_layer_section.name, element_sets.bottom_layer),
            model.SectionAssignment(top_layer_section.name, top_layer_section.name, element_sets.top_layer),
            model.SectionAssignment(global_infill_section.name, global_infill_section.name, element_sets.global_infill)
        ])

        return nmdl
