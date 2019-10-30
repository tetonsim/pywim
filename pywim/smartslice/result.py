import sys

from . import job
from .. import am, chop
from .. import Meta, WimObject, WimList, WimTuple

class StructuralAnalysis(WimObject):
    def __init__(self, name=None):
        self.name = name if name else ''
        self.min_safety_factor = 0.0
        self.max_displacement = sys.float_info.max

class Analysis(WimObject):
    def __init__(self):
        self.print_config = am.Config()
        self.structural = StructuralAnalysis()
        self.modifier_meshes = WimList(chop.mesh.Mesh)

class Result(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.analyses = []
