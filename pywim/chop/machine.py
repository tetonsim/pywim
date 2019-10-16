from .. import WimObject, WimList

class Extruder(WimObject):
    def __init__(self):
        self.diameter = 0.4
        self.slicer_settings = {}

class Printer(WimObject):
    def __init__(self, name=None):
        self.name = name if name else 'generic'
        self.extruders = WimList(Extruder)