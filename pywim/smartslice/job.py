import enum

from .. import chop, fea
from .. import Meta, WimObject, WimList

from . import  opt

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
