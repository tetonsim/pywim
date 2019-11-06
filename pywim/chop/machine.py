from .. import WimObject, WimList
from .. import am

class Extruder(WimObject):
    def __init__(self, diameter : float=0.4, config : am.Config=None):
        self.diameter = 0.4
        self.print_config = config if config else am.Config()

class Printer(WimObject):
    def __init__(self, name=None, extruders=None, config : am.Config=None):
        self.name = name if name else 'generic'
        self.extruders = WimList(Extruder)
        self.print_config = config if config else am.Config()

        if extruders:
            self.extruders.extend(extruders)