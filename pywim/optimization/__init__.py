import math
from .. import WimObject
from .. import am, fea, http, micro

try:
    import scipy
    from scipy.optimize import Bounds
except:
    from warnings import warn
    warn('Failed to import scipy. pywim.optimization will not work')

class ExtrusionTest(WimObject):
    '''
    A class which sets up the data used to test dogbones.
    '''
    def __init__(self):
        self.name = None
        self.geometry = am.Config()
        self.type = 'unfilled'
        self.density = 0.0
        self.EXY0 = None
        self.EXY90 = None
        self.EZX90 = None
        self.SXY0 = None
        self.SXY90 = None
        self.SZX90 = None

    def axial_ratio(self):
        '''
        Returns the ratio of bulk to extrusion for any axial property based on layer 
        width divided by layer height.

        This is a curve fit generated from experimental data and the extrusion
        micromechanics model.
        '''
        x = self.geometry.layer_width / self.geometry.layer_height
        return 1. / (1 - 3.6397e9 * math.exp(-24.1988981 * math.pow(x, 0.04)))

    def transverse_ratio(self, direction='Z'):
        '''
        Returns the ratio of transverse bulk stiffness to transverse extrusion stiffness 
        based on layer width divided by layer height.

        These are a curve fits generated from experimental data and the extrusion
        micromechanics model.
        '''
        x = self.geometry.layer_width / self.geometry.layer_height
        if direction == 'Y':
            return 1. / (1 - 8.0301e9 * math.exp(-24.3731764 * math.pow(x, 0.04)))

        return 1. / (1 - 4.7477e95 * math.exp(-220.731058 * math.pow(x, 0.005)))

    def transverse_yield_ratio(self):
        '''
        Returns the ratio of transverse extrusion yield strength to axial extrusion yield  
        strength based on layer width divided by layer height. If the transverse yield 
        strength of the extrusion level material is unknown, this will provide a conservative
        value for the ratio of the transverse yield strength to the longitudinal yield strength.

        This is a curve fit based on a fracture mechanics run and experimental data obtained
        from a literature review to yield a conservative transverse extrusion yield strength.
        '''
        x = self.geometry.layer_width / self.geometry.layer_height
        return 0.19 + 0.14 * x - 6.1e-3 * math.pow(x, 2)

class Config(WimObject):
    '''
    Configuration for the optimization routine
    '''
    def __init__(self):
        self.mq_url = 'amqp://guest:guest@localhost'
        self.mq_queue = 'microd'
        self.max_error = 0.01
        self.xatol = 0.001
        self.maxiter = 25

class BulkOptimization():
    '''
    Class for optimizing bulk data from extrusion data.
    '''
    def __init__(self, opt_config=None):
        self.config = opt_config if opt_config else Config()

    def run_model(self, bulk, layer_config):
        layer = micro.build.run.ExtrudedLayer(bulk, layer_config)

        wim = http.wim.Client()
        results = wim.micro.solve.post(layer)

        return results.result.materials['layer']

    def error(self, predicted, known):
        return abs((predicted - known) / known)

    def density_error(self, d, density, bulk, layer_config):
        bulk.density = d
        layer_mat = self.run_model(bulk, layer_config)

        return self.error(layer_mat.density, density)

    def axial_error(self, Eb, stiffness, bulk, layer_config):

        if bulk.elastic.type == 'isotropic':
            bulk.elastic.E = Eb
        else:
            bulk.elastic.Ea = Eb

        layer_mat = self.run_model(bulk, layer_config)

        return self.error(layer_mat.elastic.E11, stiffness)

    def transverse_error(self, Eb, stiffness, bulk, layer_config, direction='Z'):

        if bulk.elastic.type == 'isotropic':
            bulk.elastic.E = Eb
        else:
            bulk.elastic.Et = Eb

        layer_mat = self.run_model(bulk, layer_config)

        if direction == 'Y':
            return self.error(layer_mat.elastic.E22, stiffness)

        return self.error(layer_mat.elastic.E33, stiffness)

    def axial_yield_error(self, S, yield_strength, bulk, layer_config):

        bulk.failure_yield.Sy = S

        layer_mat = self.run_model(bulk, layer_config)

        return self.error(layer_mat.failure_yield.T11, yield_strength)

    def transverse_yield_error(self, kt, yield_strength, bulk, layer_config, direction='Z'):

        bulk.fracture.KIc = kt

        layer_mat = self.run_model(bulk, layer_config)

        if direction == 'Y':
            return self.error(layer_mat.failure_yield.T22, yield_strength)

        return self.error(layer_mat.failure_yield.T33, yield_strength)

    def axial_bounds(self, x):
        '''
        Returns the upper and lower bounds of the of the bulk axial property to the extrusion
        axial property. This works for axial stiffness, axial yield strength and density.

        The numbers are curve fits based on normalized data ran from the extrusion micromechanics
        model and physical reality.
        '''
        return (x, x / 0.88)

    def transverse_bounds(self, x, direction='Y'):
        '''
        Returns the upper and lower bounds of the of the bulk transverse stiffness to the extrusion
        transverse stiffness based on the input direction.

        The numbers are curve fits based on normalized data ran from the extrusion micromechanics
        model and physical reality.
        '''
        if (direction == 'Y'):
            return (x, x / 0.80)

        return (x, x / 0.35)

    def toughness_bounds(self, x, direction='Y'):
        '''
        Returns the upper and lower bounds of the of the bulk fracture toughness to the extrusion
        transverse yield strength based on the input direction.

        The numbers are curve fits based on normalized data ran from the extrusion micromechanics
        model.
        '''
        if (direction == 'Y'):
            return (x * 0.1, x * 0.8)

        return (x * 0.1, x * 1.5)

    def minimize(self, opt_fun=None, opt_args=None, opt_bounds=None, tol=1.e-3):
        res = scipy.optimize.minimize_scalar(fun=opt_fun, method='bounded', args=opt_args, bounds=opt_bounds, 
                                             options={'xatol': tol, 'maxiter': self.config.maxiter})
        return res.x

def optimize_bulk(test_data : ExtrusionTest, config : Config = None):
    '''
    This routine optimizes bulk material data based on measured extrusion layer data.
    '''

    if config is None:
        config = Config()

    EX = test_data.EXY0
    EY = test_data.EXY90
    EZ = test_data.EZX90

    SX = test_data.SXY0
    SY = test_data.SXY90
    SZ = test_data.SZX90

    if test_data.type == 'filled' and EY is None and EZ is None:
        raise Exception('A transverse stiffness of type XY90 or ZX90 needs to be supplied for filled materials')

    if test_data.type == 'filled' and SY is None and SZ is None:
        raise Exception('A transverse yield strength of type XY90 or ZX90 needs to be supplied for filled materials')

    # Setup the first guess for the bulk material
    bulk = model.Material('bulk')

    bulk.density = test_data.axial_ratio() * test_data.density

    Ea = test_data.axial_ratio() * EX
    Et = Ea
    nuat = 0.4
    nutt = 0.35
    Gat = 0.6 * Ea

    Sy = test_data.axial_ratio() * SX
    KIc = 6.0

    if test_data.type == 'unfilled':
        bulk.elastic = fea.model.Elastic(type = 'isotropic', properties = {'E': Ea, 'nu': nutt})
    else:
        if EY is not None:
            Et = test_data.transverse_ratio('Y') * EY
        else:
            Et = test_data.transverse_ratio('Z') * EZ

        bulk.elastic = fea.model.Elastic(type = 'transverse_isotropic', properties = {'Ea': Ea, 'Et': Et, 
                                           'nuat': nuat, 'nutt': nutt, 'Gat': Gat})

    bulk.failure_yield = fea.model.Yield(type = 'von_mises', properties = {'Sy': Sy})
    bulk.fracture = fea.model.Fracture(KIc)


    bulk_opt = BulkOptimization(opt_config=config)

    mat_0 = bulk_opt.run_model(bulk, test_data.geometry)

    # Optimize the axial modulus
    if bulk_opt.error(mat_0.elastic.E11, EX) > config.max_error:
        Ea = bulk_opt.minimize(bulk_opt.axial_error, (EX, bulk, test_data.geometry), bulk_opt.axial_bounds(EX), config.xatol * EX)

    # Optimize transverse modulus for filled materials
    if test_data.type == 'unfilled':
        bulk.elastic.E = Ea

    else:
        if EY is not None and bulk_opt.error(mat_0.elastic.E22, EY) > config.max_error:
            Et = bulk_opt.minimize(bulk_opt.transverse_error, (EY, bulk, test_data.geometry, 'Y'), bulk_opt.transverse_bounds(EY, 'Z'), 
                                                               config.xatol * EY)

        elif EZ is not None and bulk_opt.error(mat_0.elastic.E33, EZ) > config.max_error:
            Et = bulk_opt.minimize(bulk_opt.transverse_error, (EZ, bulk, test_data.geometry, 'Z'), bulk_opt.transverse_bounds(EZ, 'Z'), 
                                                               config.xatol * EZ)

        bulk.elastic.Ea = Ea
        bulk.elastic.Et = Et

    # Optimize the bulk yield strength
    if bulk_opt.error(mat_0.failure_yield.T11, SX) > config.max_error:
        bulk.failure_yield.Sy = bulk_opt.minimize(bulk_opt.axial_yield_error, (SX, bulk, test_data.geometry), bulk_opt.axial_bounds(SX), 
                                                  config.xatol * SX)

    # Optimize the fracture toughness
    if SY is not None and bulk_opt.error(mat_0.failure_yield.T22, SY) > config.max_error:
        bulk.fracture.KIc = bulk_opt.minimize(bulk_opt.transverse_yield_error, (SY, bulk, test_data.geometry, 'Y'), bulk_opt.toughness_bounds(SY, 'Y'), 
                                              config.xatol * SY)

    elif SZ is not None and bulk_opt.error(mat_0.failure_yield.T33, SZ) > config.max_error:
        bulk.fracture.KIc = bulk_opt.minimize(bulk_opt.transverse_yield_error, (SZ, bulk, test_data.geometry, 'Z'), bulk_opt.toughness_bounds(SZ, 'Z'), 
                                              config.xatol * SZ)

    else:
        SY = test_data.transverse_yield_ratio() * SX
        bulk.fracture.KIc = bulk_opt.minimize(bulk_opt.transverse_yield_error, (SY, bulk, test_data.geometry, 'Y'), bulk_opt.toughness_bounds(SY, 'Y'), 
                                              config.xatol * SY)

    # Optimize the density of the material
    if test_data.density > 0.0 and bulk_opt.error(mat_0.density, test_data.density) > config.max_error:
        bulk.density = bulk_opt.minimize(bulk_opt.density_error, (test_data.density, bulk, test_data.geometry), 
                                         bulk_opt.axial_bounds(test_data.density), config.xatol * test_data.density)

    return bulk

