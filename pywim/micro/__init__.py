from .. import WimObject, WimList, WimTuple, am, model

class UnitCell(WimObject):
    def __init__(self, unit_cell):
        self.unit_cell = unit_cell

class Composite(WimObject):
    def __init__(self, fiber : model.Material, matrix : model.Material, volume_fraction, L_over_D=None):
        self.fiber = fiber
        self.matrix = matrix
        self.volume_fraction = volume_fraction
        self.L_over_D = L_over_D

        if self.volume_fraction < 1.0:
            self.volume_fraction *= 100.0

        self.volume_fraction = round(self.volume_fraction)

class Hexpack(UnitCell):
    def __init__(self, volume_fraction):
        super().__init__('continuous_hexagonal_pack')
        self.volume_fraction = volume_fraction

class ParticulateBCC(UnitCell):
    def __init__(self, volume_fraction):
        super().__init__('spherical_particulate_bcc')
        self.volume_fraction = volume_fraction

class ShortFiber(UnitCell):
    def __init__(self, volume_fraction, L_over_D):
        super().__init__('short_fiber')
        self.volume_fraction = volume_fraction
        self.L_over_D = L_over_D

class ExtrudedLayer(UnitCell):
    def __init__(self, config : am.Config):
        super().__init__('solid_layer')
        self.layer_width = config.layer_width
        self.layer_height = config.layer_height
        self.overlap = None #am.Config.default_overlap(config.layer_height)
        self.mesh_seed = 0.1

class Infill(UnitCell):
    def __init__(self, unit_cell, volume_fraction, layer_width):
        super().__init__(unit_cell)
        self.volume_fraction = volume_fraction
        self.layer_width = layer_width

    @staticmethod
    def FromConfig(config : am.Config):
        if config.infill.pattern == am.InfillType.grid:
            return InfillSquare(config.infill.density, config.layer_width)
        elif config.infill.pattern == am.InfillType.triangle:
            return InfillTriangle(config.infill.density, config.layer_width)
        
        raise Exception(f'Unrecognized infill unit cell name: {config.infill.pattern}')

class InfillSquare(Infill):
    def __init__(self, volume_fraction, layer_width):
        super().__init__('infill_square', volume_fraction, layer_width)
        self.mesh_seed = 0.5

class InfillTriangle(Infill):
    def __init__(self, volume_fraction, layer_width):
        super().__init__('infill_triangle', volume_fraction, layer_width)
        self.mesh_seed = 0.1

class JobMaterial(WimObject):
    def __init__(self, name, source, source_name):
        self.name = name
        self.source = source
        self.source_name = source_name

    @classmethod
    def FromMaterial(cls, name, source_name):
        return cls(name, 'materials', source_name)
    
    @classmethod
    def FromJob(cls, name, source_name):
        return cls(name, 'job', source_name)

class Job(WimObject):
    def __init__(self, name, geometry):
        self.name = name
        self.geometry = geometry
        self.materials = WimList(JobMaterial)

class Tree(WimObject):
    def __init__(self):
        self.materials = WimList(model.Material)
        self.jobs = WimList(Job)

class Run(WimObject):
    def __init__(self, input : Tree, target : str):
        self.input = input
        self.target = target
        self.all = False

class Result(WimObject):
    def __init__(self):
        self.meta = {}
        self.materials = WimList(model.Material)

from . import build
