import pywim
import time
import scipy
import numpy
from scipy.optimize import Bounds

tests = {'X': 'XX', 'Y': 'XY', 'Z': 'ZX'}
max_error = 0.01

def axial_ratio(config):
    x = config.layer_width / config.layer_height
    return 1. / (1 - 3.6397e9 * numpy.exp(-24.1988981 * numpy.power(x, 0.04)))


def transverse_ratio(config, direction='Z'):
    x = config.layer_width / config.layer_height
    if (direction == 'Y'):
        return 1. / (1 - 8.0301e9 * numpy.exp(-24.3731764 * numpy.power(x, 0.04)))
    
    return 1. / (1 - 4.7477e95 * numpy.exp(-220.731058 * numpy.power(x, 0.005)))

def transverse_yield_ratio(config):
    return 0.47

def run_model(bulk, config):
    layer = pywim.micro.build.run.ExtrudedLayer(bulk, config)

    micro_agent = pywim.job.Agent.Micromechanics('amqp://guest:guest@localhost', 'microd-moran-in')
    results = micro_agent.run_sync(layer)

    return results.result.materials['layer']


def error(predicted, known):
    return numpy.abs((predicted - known) / known)


def density_error(d, density, bulk, config):
    bulk.density = d
    layer_mat = run_model(bulk, config)

    return error(layer_mat.density, density)


def axial_error(Eb, stiffness, bulk, config):
    
    if (bulk.elastic.type == 'isotropic'):
        bulk.elastic.E = Eb
    else:
        bulk.elastic.Ea = Eb
    
    layer_mat = run_model(bulk, config)

    return error(layer_mat.elastic.E11, stiffness)


def transverse_error(Eb, stiffness, bulk, config, direction='Z'):

    if (bulk.elastic.type == 'isotropic'):
        bulk.elastic.E = Eb
    else:
        bulk.elastic.Et = Eb

    layer_mat = run_model(bulk, config)

    if (direction == 'Y'):
        return error(layer_mat.elastic.E22, stiffness)

    return error(layer_mat.elastic.E33, stiffness)

def axial_yield_error(S, yield_strength, bulk, config):

    bulk.failure_yield.Sy = S

    layer_mat = run_model(bulk, config)

    return error(layer_mat.failure_yield.T11, yield_strength)

def transverse_yield_error(kt, yield_strength, bulk, config, direction='Z'):

    bulk.fracture.KIc = kt

    layer_mat = run_model(bulk, config)

    if (direction == 'Y'):
        return error(layer_mat.failure_yield.T22, yield_strength)

    return error(layer_mat.failure_yield.T33, yield_strength)

def optimize_bulk(stiffnesses, strengths, density=0.0, config=None, type='unfilled'):

    if (type == 'filled' and tests['Y'] not in stiffnesses.keys() and tests['Z'] not in stiffnesses.keys()):
        raise Exception('A transverse stiffness of type Y or Z was not supplied for the filled material')

    bulk = pywim.model.Material('bulk')

    Ea = axial_ratio(config) * stiffnesses[tests['X']]
    Et = Ea
    nuat = 0.4
    nutt = 0.35
    Gat = 0.6 * Ea

    S11 = axial_ratio(config) * strengths[tests['X']]
    kc_mode1 = 6.0

    # Set the material properties depending on if the material is filled or unfilled
    bulk.density = axial_ratio(config) * density
    if (type == 'unfilled'):
        bulk.elastic = pywim.model.Elastic(type = 'isotropic', properties = {'E': Ea, 'nu': nutt})
    else:
        if (tests['Y'] in stiffnesses.keys()):
            Et = transverse_ratio(config, 'Y') * stiffnesses[tests['Y']]
        else:
            Et = transverse_ratio(config, 'Z') * stiffnesses[tests['Z']]

        bulk.elastic = pywim.model.Elastic(type = 'transverse_isotropic', properties = {'Ea': Ea, 'Et': Et, 
                                           'nuat': nuat, 'nutt': nutt, 'Gat': Gat})

    bulk.failure_yield = pywim.model.Yield(type = 'von_mises', properties = {'Sy': S11})
    bulk.fracture = pywim.model.Fracture(properties = {'KIc': kc_mode1})

    # Run the micromechanics model with the base material definition
    mat_0 = run_model(bulk, config)
    
    # Optimize the axial modulus
    if (error(mat_0.elastic.E11, stiffnesses[tests['X']]) > max_error):
        axial_res = scipy.optimize.minimize_scalar(fun=axial_error, method='bounded', args=(stiffnesses[tests['X']], bulk, config), 
                                                   bounds=(stiffnesses[tests['X']], stiffnesses[tests['X']] / 0.88),
                                                   options={'xatol': 1.e-3 * stiffnesses[tests['X']], 'maxiter': 25})
        Ea = axial_res.x
    
    # Optimize transverse modulus for filled materials
    if (type == 'unfilled'):
        bulk.elastic.E = Ea

    else:
    
        if (tests['Y'] in stiffnesses.keys() and error(mat_0.elastic.E22, stiffnesses[tests['Y']]) > max_error):
            transverse_res = scipy.optimize.minimize_scalar(fun=transverse_error, method='bounded', args=(stiffnesses[tests['Y']], bulk, config, 'Y'), 
                                                            bounds=(stiffnesses[tests['Y']], stiffnesses[tests['Y']] / 0.8),
                                                            options={'xatol': 1.e-3 * stiffnesses[tests['Y']], 'maxiter': 25})

            Et = transverse_res.x

        elif (tests['Z'] in stiffnesses.keys() and error(mat_0.elastic.E33, stiffnesses[tests['Z']]) > max_error):
            transverse_res = scipy.optimize.minimize_scalar(fun=transverse_error, method='bounded', args=(stiffnesses[tests['Z']], bulk, config, 'Z'), 
                                                            bounds=(stiffnesses[tests['Z']], stiffnesses[tests['Z']] / 0.35),
                                                            options={'xatol': 1.e-3 * stiffnesses[tests['Z']], 'maxiter': 25})

            Et = transverse_res.x

        bulk.elastic.Ea = Ea
        bulk.elastic.Et = Et

    # Optimize the bulk yield strength
    if (mat_0.failure_yield.T11, strengths[tests['X']] > max_error):

        axial_yield_res = scipy.optimize.minimize_scalar(fun=axial_yield_error, method='bounded', args=(strengths[tests['X']], bulk, config), 
                                                        bounds=(strengths[tests['X']], strengths[tests['X']] / 0.88),
                                                        options={'xatol': 1.e-3 * strengths[tests['X']], 'maxiter': 25})
        bulk.failure_yield.S = axial_yield_res.x

    # Optimize the fracture toughness
    if (tests['Y'] in strengths.keys() and error(mat_0.failure_yield.T22, strengths[tests['Y']]) > max_error):
        transverse_yield_res = scipy.optimize.minimize_scalar(fun=transverse_yield_error, method='bounded', args=(strengths[tests['Y']], bulk, config, 'Y'), 
                                                              bounds=(strengths[tests['Y']] * 0.1, strengths[tests['Y']] * 0.8),
                                                              options={'xatol': 1.e-3 * strengths[tests['Y']], 'maxiter': 25})

        bulk.fracture.kc = transverse_yield_res.x

    elif (tests['Z'] in strengths.keys() and error(mat_0.failure_yield.T33, strengths[tests['Z']]) > max_error):
        transverse_yield_res = scipy.optimize.minimize_scalar(fun=transverse_yield_error, method='bounded', args=(strengths[tests['Z']], bulk, config, 'Z'), 
                                                              bounds=(strengths[tests['Z']] * 0.1, strengths[tests['Z']] * 1.5),
                                                              options={'xatol': 1.e-3 * strengths[tests['Z']], 'maxiter': 25})

        bulk.fracture.kc = transverse_yield_res.x
    else:
        T22 = transverse_yield_ratio(config) * strengths[tests['X']]
        transverse_yield_res = scipy.optimize.minimize_scalar(fun=transverse_yield_error, method='bounded', args=(T22, bulk, config, 'Y'), 
                                                              bounds=(T22 * 0.1, T22 * 0.8), options={'xatol': 1.e-3 * T22, 'maxiter': 25})

        bulk.fracture.kc = transverse_yield_res.x


    # Optimize the density of the material
    if (density > 0.0 and error(mat_0.density, density) > max_error):
        res = scipy.optimize.minimize_scalar(fun=density_error, args=(density, bulk, config), method='bounded',
                                             bounds=(density, density / 0.88), options={'xatol':1.e-3 * density, 'maxiter': 25})
        bulk.density = res.x

    return bulk
 
# if __name__ == '__main__':
#     config = pywim.am.Config()
#     config.layer_height = 0.2
#     config.layer_width = 0.4
#     bulk = optimize_bulk({tests['X']: 1.61e3}, {tests['X']: 29.63, tests['Y']: 13.83}, 1.18, config, type='unfilled')
    
#     print ("Density: %f" % bulk.density)
#     print ("E: %f" % bulk.elastic.E)
#     print ("S: %f" % bulk.failure_yield.S)
#     print ("KIc: %f" % bulk.fracture.KIc)
