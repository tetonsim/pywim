from . import WimObject, WimList

class Infill(WimObject):
    def __init__(self):
        self.pattern = 'grid'
        self.density = 50
        self.orientation = 0.0

class Layer(WimObject):
    def __init__(self, orientation=0.0):
        self.orientation = orientation

class Stack(WimObject):
    def __init__(self):
        self.layers = WimList(Layer)

    @property
    def count(self):
        return len(self.layers)

    @classmethod
    def Cycle(cls, count, orientations):
        stack = cls()

        nori = len(orientations)
        if nori == 0:
            nori = 1
            orientations = [0.0]

        i = 0
        l = 0
        while i < max(1, count):
            lay = Layer(orientations[l])
            stack.layers.append( lay )
            
            i += 1
            l += 1

            if l == nori:
                l = 0

        return stack

class Config(WimObject):
    def __init__(self):
        self.layer_width = 0.45
        self.layer_height = 0.2
        self.walls = 2
        self.bottom_layer = Stack.Cycle(6, [45., -45.])
        self.top_layer = Stack.Cycle(6, [45., -45.])
        self.infill = Infill()
