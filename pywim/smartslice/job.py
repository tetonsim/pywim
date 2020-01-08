import enum

from .. import chop, fea
from .. import Meta, WimObject, WimList

from . import  opt

class JobType(enum.Enum):
    validation = 1
    optimization = 2

class Job(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.type = JobType.validation
        self.chop = chop.model.Model()
        self.bulk = WimList(fea.model.Material)
        self.optimization = opt.Optimization()
