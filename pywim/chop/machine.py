from .. import WimObject, WimList

class Extruder(WimObject):
    def __init__(self, diameter : float=0.4, settings : dict=None):
        self.diameter = 0.4
        self.settings = settings if settings else {}

class Printer(WimObject):
    def __init__(self, name=None, extruders=None, settings : dict=None):
        self.name = name if name else 'generic'
        self.extruders = WimList(Extruder)
        self.settings = settings if settings else {}

        if extruders:
            self.extruders.extend(extruders)