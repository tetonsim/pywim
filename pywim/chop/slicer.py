from .. import WimObject, WimList

from . import machine

class Config(WimObject):
    def __init__(self, printer : machine.Printer=None, settings : dict=None):
        self.printer = machine.Printer()
        self.settings = settings if settings else {}

class Slicer(WimObject):
    DEFAULTTYPENAME = 'cura'
    def __init__(self, config : Config=None):
        self.type = None
        self.config = config if config else Config()

class CuraEngine(Slicer):
    JSONTYPENAME = 'cura'
    def __init__(self, config : Config=None):
        super().__init__(config)
        self.type = CuraEngine.JSONTYPENAME
