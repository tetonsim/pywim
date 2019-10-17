import enum

from .. import chop, fea
from .. import Meta, WimObject, WimList, WimTuple, WimIgnore

from . import  opt

class JobType(enum.Enum):
    validation = 1
    optimization = 2

class Job(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.type = JobType.validation
        self.chop = chop.job.Job()
        #self.mesh = chop.mesh.Mesh()
        self.bulk = fea.model.Material()
        self.optimization = opt.Optimization()
