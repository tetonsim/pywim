from .. import WimObject, WimList

from . import machine

class SliceConfiguration(WimObject):
    def __init__(self):
        self.printer = machine.Printer()
        self.extruders = WimList(machine.Extruder)
        self.slicer_settings = {}

class Slicer(WimObject):
    DEFAULTTYPENAME = 'cura'
    def __init__(self):
        self.type = None
        self.configuration = SliceConfiguration()

class CuraEngine(Slicer):
    JSONTYPENAME = 'cura'
    def __init__(self):
        super().__init__()
        self.type = CuraEngine.JSONTYPENAME
