import enum
from pywim import chop

from .. import WimObject, WimList, WimTuple, WimIgnore

class NumOptParam(WimObject):
    '''
    Numerical optimization parmater class. Treated as a discrete variable with given min, max, and increment.
    '''
    def __init__(self, name='num_name', minimum=1., maximum=1., number_of_steps=0, active=False, mesh_type=chop.mesh.MeshType.normal):
        self.name = name
        self.min = minimum
        self.max = maximum
        self.num_steps = number_of_steps
        self.active = active
        self.mesh_type = mesh_type

    @property
    def inc(self):
        return (self.max - self.min) / self.num_steps

    @property
    def interval(self):
        if self.min == self.max:
            return [self.min]
        else:
            return [self.min, self.max]

    @property
    def range(self):
        return self.max - self.min

class CatOptParam(WimObject):
    '''
    Categorical optimization parameter class.
    '''
    def __init__(self, name='cat_name', cats=None, active=False, mesh_type=chop.mesh.MeshType.normal):
        self.name = name
        self.cats = cats if cats else []
        self.active = active
        self.mesh_type = mesh_type

class ModifierMeshCriteria(enum.Enum):
    selden = 1

class ModifierMesh(WimObject):
    def __init__(self, min_score=50.0):
        self.criterion = ModifierMeshCriteria.selden
        self.min_score = min_score

class OptimizimationTarget(enum.Enum):
    cura_print_time = 1
    cura_material_volume = 2

class Optimization(WimObject):
    def __init__(self):
        self.number_of_results_requested = 5
        self.min_safety_factor = 2.0
        self.max_displacement = 1.0
        self.optimization_target = OptimizimationTarget.cura_print_time
        self.numerical_parameters = WimList(NumOptParam)
        self.categorical_parameters = WimList(CatOptParam)
        self.modifier_meshes = WimList(ModifierMesh)
        self.min_element_in_mod_mesh = 10
        self.min_percentile_mod_mesh = 1.
        self.max_percentile_mod_mesh = 99.

        # default modifier mesh config
        self.modifier_meshes.extend(
            (
                ModifierMesh(min_score=80.0),
            )
        )

        # default numerical parameters
        self.numerical_parameters.extend(
            (
                NumOptParam(
                    name='infill.density',
                    minimum=20.,
                    maximum=95.,
                    number_of_steps=15,
                    active=True
                ),
                NumOptParam(
                    name='walls',
                    minimum=2,
                    maximum=6,
                    number_of_steps=4,
                    active=True
                ),
                NumOptParam(
                    name='skins',
                    minimum=2,
                    maximum=6,
                    number_of_steps=4,
                    active=True
                ),
                NumOptParam(
                    name='infill.density',
                    minimum=20.,
                    maximum=95.,
                    number_of_steps=15,
                    mesh_type=chop.mesh.MeshType.infill,
                    active=True
                ),
                NumOptParam(
                    name='walls',
                    minimum=2.,
                    maximum=6,
                    number_of_steps=4,
                    mesh_type=chop.mesh.MeshType.infill,
                    active=False
                ),
                NumOptParam(
                    name='skins',
                    minimum=2,
                    maximum=6,
                    number_of_steps=4,
                    mesh_type=chop.mesh.MeshType.infill,
                    active=False
                )
            )
        )

    @property
    def active_numerical_parameters(self):
        return [p for p in self.numerical_parameters if p.active]

    @property
    def active_categorical_parameters(self):
        return [p for p in self.categorical_parameters if p.active]

    def adjust_numerical_parameter_setting(self, name, mesh_type, setting_name, new_value):
        for p in self.numerical_parameters:
            if p.name == name and p.mesh_type == mesh_type:
                setattr(p, setting_name, new_value)

    def set_activity_numerical_parameter(self, name, mesh_type, active):
        for p in self.numerical_parameters:
            if p.name == name and p.mesh_type == mesh_type:
                p.active = active

    def set_activity_categorical_parameter(self, name, mesh_type, active):
        for p in self.categorical_parameters:
            if p.name == name and p.mesh_type == mesh_type:
                p.active = active

