import enum

from .. import WimObject, WimList, WimTuple, WimIgnore

class ModifierMeshCriteria(enum.Enum):
    selden = 1

class ModifierMesh(WimObject):
    def __init__(self, min_score=0.5):
        self.criterion = ModifierMeshCriteria.selden
        self.min_score = min_score

class Optimization(WimObject):
    def __init__(self):
        self.min_safety_factor = 2.0
        self.max_displacement = 1.0
        self.number_exploration_points = 2
        self.optimize_global_infill_density = True
        self.infill_density_minimum = 20.0
        self.infill_density_maximum = 95.0
        self.infill_density_increment = 5.0
        self.modifier_meshes = WimList(ModifierMesh)

        # default modifier mesh config
        self.modifier_meshes.extend(
            (
                ModifierMesh(0.33),
                ModifierMesh(0.67)
            )
        )