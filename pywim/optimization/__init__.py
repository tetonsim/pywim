import pywim
import time
import scipy
import numpy
from .. import WimObject
from scipy.optimize import Bounds

# Global variables which can be overidden with a configuration file
tests = {'X': 'XY0', 'Y': 'XY90', 'Z': 'ZX90'}
micro_url = 'amqp://guest:guest@localhost'
micro_queue = 'microd' 
max_error = 0.01
xatol = 1.e-3
maxiter = 25

class Config(WimObject):
    def __init__(self):
        self.test_names = tests
        self.micro_url = micro_url
        self.micro_queue = micro_queue
        self.max_error = max_error
        self.xatol = xatol
        self.maxiter = maxiter

def axial_ratio(layer_config):
    x = layer_config.layer_width / layer_config.layer_height
    return 1. / (1 - 3.6397e9 * numpy.exp(-24.1988981 * numpy.power(x, 0.04)))

def transverse_ratio(layer_config, direction='Z'):
    x = layer_config.layer_width / layer_config.layer_height
    if (direction == 'Y'):
        return 1. / (1 - 8.0301e9 * numpy.exp(-24.3731764 * numpy.power(x, 0.04)))
    
    return 1. / (1 - 4.7477e95 * numpy.exp(-220.731058 * numpy.power(x, 0.005)))

def transverse_yield_ratio(layer_config):
    x = layer_config.layer_width / layer_config.layer_height
    return 0.19 + 0.14 * x - 6.1e-3 * x * x

def run_model(bulk, layer_config):
    layer = pywim.micro.build.run.ExtrudedLayer(bulk, layer_config)

    micro_agent = pywim.job.Agent.Micromechanics(micro_url, micro_queue)
    results = micro_agent.run_sync(layer)

    return results.result.materials['layer']

def error(predicted, known):
    return numpy.abs((predicted - known) / known)

def density_error(d, density, bulk, layer_config):
    bulk.density = d
    layer_mat = run_model(bulk, layer_config)

    return error(layer_mat.density, density)

def axial_error(Eb, stiffness, bulk, layer_config):
    
    if (bulk.elastic.type == 'isotropic'):
        bulk.elastic.E = Eb
    else:
        bulk.elastic.Ea = Eb
    
    layer_mat = run_model(bulk, layer_config)

    return error(layer_mat.elastic.E11, stiffness)

def transverse_error(Eb, stiffness, bulk, layer_config, direction='Z'):

    if (bulk.elastic.type == 'isotropic'):
        bulk.elastic.E = Eb
    else:
        bulk.elastic.Et = Eb

    layer_mat = run_model(bulk, layer_config)

    if (direction == 'Y'):
        return error(layer_mat.elastic.E22, stiffness)

    return error(layer_mat.elastic.E33, stiffness)

def axial_yield_error(S, yield_strength, bulk, layer_config):

    bulk.failure_yield.Sy = S

    layer_mat = run_model(bulk, layer_config)

    return error(layer_mat.failure_yield.T11, yield_strength)

def transverse_yield_error(kt, yield_strength, bulk, layer_config, direction='Z'):

    bulk.fracture.KIc = kt

    layer_mat = run_model(bulk, layer_config)

    if (direction == 'Y'):
        return error(layer_mat.failure_yield.T22, yield_strength)

    return error(layer_mat.failure_yield.T33, yield_strength)

def optimize_bulk(stiffnesses, strengths, density=0.0, layer_config=None, type='unfilled', opt_config=None):

    global tests
    global micro_url
    global micro_queue
    global max_error
    global maxiter
    global xatol
    
    if (opt_config != None):
        tests = opt_config.test_names
        micro_queue = opt_config.micro_queue
        micro_url = opt_config.micro_url
        max_error = opt_config.max_error
        maxiter = opt_config.maxiter
        xatol = opt_config.xatol

    if (type == 'filled' and tests['Y'] not in stiffnesses.keys() and tests['Z'] not in stiffnesses.keys()):
        raise Exception('A transverse stiffness of type Y or Z was not supplied for the filled material')

    bulk = pywim.model.Material('bulk')

    Ea = axial_ratio(layer_config) * stiffnesses[tests['X']]
    Et = Ea
    nuat = 0.4
    nutt = 0.35
    Gat = 0.6 * Ea

    S11 = axial_ratio(layer_config) * strengths[tests['X']]
    kc_mode1 = 6.0

    # Set the material properties depending on if the material is filled or unfilled
    bulk.density = axial_ratio(layer_config) * density
    if (type == 'unfilled'):
        bulk.elastic = pywim.model.Elastic(type = 'isotropic', properties = {'E': Ea, 'nu': nutt})
    else:
        if (tests['Y'] in stiffnesses.keys()):
            Et = transverse_ratio(layer_config, 'Y') * stiffnesses[tests['Y']]
        else:
            Et = transverse_ratio(layer_config, 'Z') * stiffnesses[tests['Z']]

        bulk.elastic = pywim.model.Elastic(type = 'transverse_isotropic', properties = {'Ea': Ea, 'Et': Et, 
                                           'nuat': nuat, 'nutt': nutt, 'Gat': Gat})

    bulk.failure_yield = pywim.model.Yield(type = 'von_mises', properties = {'Sy': S11})
    bulk.fracture = pywim.model.Fracture(properties = {'KIc': kc_mode1})

    # Run the micromechanics model with the base material definition
    mat_0 = run_model(bulk, layer_config)
    
    # Optimize the axial modulus
    if (error(mat_0.elastic.E11, stiffnesses[tests['X']]) > max_error):
        axial_res = scipy.optimize.minimize_scalar(fun=axial_error, method='bounded', args=(stiffnesses[tests['X']], bulk, layer_config), 
                                                   bounds=(stiffnesses[tests['X']], stiffnesses[tests['X']] / 0.88),
                                                   options={'xatol': xatol * stiffnesses[tests['X']], 'maxiter': maxiter})
        Ea = axial_res.x
    
    # Optimize transverse modulus for filled materials
    if (type == 'unfilled'):
        bulk.elastic.E = Ea

    else:
    
        if (tests['Y'] in stiffnesses.keys() and error(mat_0.elastic.E22, stiffnesses[tests['Y']]) > max_error):
            transverse_res = scipy.optimize.minimize_scalar(fun=transverse_error, method='bounded', args=(stiffnesses[tests['Y']], bulk, layer_config, 'Y'), 
                                                            bounds=(stiffnesses[tests['Y']], stiffnesses[tests['Y']] / 0.8),
                                                            options={'xatol': xatol * stiffnesses[tests['Y']], 'maxiter': maxiter})

            Et = transverse_res.x

        elif (tests['Z'] in stiffnesses.keys() and error(mat_0.elastic.E33, stiffnesses[tests['Z']]) > max_error):
            transverse_res = scipy.optimize.minimize_scalar(fun=transverse_error, method='bounded', args=(stiffnesses[tests['Z']], bulk, layer_config, 'Z'), 
                                                            bounds=(stiffnesses[tests['Z']], stiffnesses[tests['Z']] / 0.35),
                                                            options={'xatol': xatol * stiffnesses[tests['Z']], 'maxiter': maxiter})

            Et = transverse_res.x

        bulk.elastic.Ea = Ea
        bulk.elastic.Et = Et

    # Optimize the bulk yield strength
    if (mat_0.failure_yield.T11, strengths[tests['X']] > max_error):

        axial_yield_res = scipy.optimize.minimize_scalar(fun=axial_yield_error, method='bounded', args=(strengths[tests['X']], bulk, layer_config), 
                                                        bounds=(strengths[tests['X']], strengths[tests['X']] / 0.88),
                                                        options={'xatol': xatol * strengths[tests['X']], 'maxiter': maxiter})
        bulk.failure_yield.Sy = axial_yield_res.x

    # Optimize the fracture toughness
    if (tests['Y'] in strengths.keys() and error(mat_0.failure_yield.T22, strengths[tests['Y']]) > max_error):
        transverse_yield_res = scipy.optimize.minimize_scalar(fun=transverse_yield_error, method='bounded', args=(strengths[tests['Y']], bulk, layer_config, 'Y'), 
                                                              bounds=(strengths[tests['Y']] * 0.1, strengths[tests['Y']] * 0.8),
                                                              options={'xatol': xatol * strengths[tests['Y']], 'maxiter': maxiter})

        bulk.fracture.KIc = transverse_yield_res.x

    elif (tests['Z'] in strengths.keys() and error(mat_0.failure_yield.T33, strengths[tests['Z']]) > max_error):
        transverse_yield_res = scipy.optimize.minimize_scalar(fun=transverse_yield_error, method='bounded', args=(strengths[tests['Z']], bulk, layer_config, 'Z'), 
                                                              bounds=(strengths[tests['Z']] * 0.1, strengths[tests['Z']] * 1.5),
                                                              options={'xatol': xatol * strengths[tests['Z']], 'maxiter': maxiter})

        bulk.fracture.KIc = transverse_yield_res.x
    else:
        T22 = transverse_yield_ratio(layer_config) * strengths[tests['X']]
        transverse_yield_res = scipy.optimize.minimize_scalar(fun=transverse_yield_error, method='bounded', args=(T22, bulk, layer_config, 'Y'), 
                                                              bounds=(T22 * 0.1, T22 * 0.8), options={'xatol': xatol * T22, 'maxiter': maxiter})

        bulk.fracture.KIc = transverse_yield_res.x


    # Optimize the density of the material
    if (density > 0.0 and error(mat_0.density, density) > max_error):
        res = scipy.optimize.minimize_scalar(fun=density_error, args=(density, bulk, layer_config), method='bounded',
                                             bounds=(density, density / 0.88), options={'xatol':xatol * density, 'maxiter': maxiter})
        bulk.density = res.x

    return bulk

