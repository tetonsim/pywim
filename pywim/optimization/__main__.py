import os
import sys
import json
import pywim
from . import *

def main():
    if len(sys.argv) < 2:
        usage()
        return

    # Grab the configuration file if it exists
    pconfig = os.path.isfile('opt.config')

    if (pconfig):
        with open('opt.config', 'r') as fconfig:
            oconfig = Config().from_json(json.dumps(json.load(fconfig)))
    else:
        oconfig = Config()

    # Retreive the input file and set the inputs to the optimization routine
    jopt = sys.argv[1]

    with open(jopt, 'r') as fopt:
        dopt = json.load(fopt)

    layer_config = pywim.am.Config().from_json(json.dumps(dopt['geometry']))

    name = dopt['name']
    bulk_type = dopt['type']
    density = dopt['density']
    stiffnesses = dopt['stiffness']
    strengths = dopt['yield_strength']

    bulk_mat = optimize_bulk(stiffnesses, strengths, density, layer_config, bulk_type, oconfig)
    bulk_mat.name = name + '_bulk'

    jrst = f'{jopt}.bulk'

    with open(jrst, 'w') as f:
        json.dump(pywim.ModelEncoder.object_to_dict(bulk_mat), f)

def usage():
    print('Usage:')
    print(f'{sys.argv[0]} JSON')
    print('Optimizes bulk material properties for a known set of coupon data defined in JSON format.')

if __name__ == '__main__':
    main()
