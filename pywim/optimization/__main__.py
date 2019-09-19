import os
import sys
import json
from . import BulkOptimization, ExtrusionTest, Config, optimize_bulk
from .. import ModelEncoder

def main():
    if len(sys.argv) < 2:
        usage()
        return

    # Grab the configuration file if it exists
    pconfig = os.path.isfile('opt.config')

    if (pconfig):
        oconfig = Config.model_from_file('opt.config')
    else:
        oconfig = Config()

    jopt = sys.argv[1]

    extrusion_test = ExtrusionTest.model_from_file(jopt)

    bulk_mat = optimize_bulk(extrusion_test, oconfig)
    bulk_mat.name = extrusion_test.name + '_bulk'

    jrst = f'{jopt}.bulk'

    with open(jrst, 'w') as f:
        json.dump(ModelEncoder.object_to_dict(bulk_mat), f)

def usage():
    print('Usage:')
    print(f'{sys.argv[0]} JSON')
    print('Optimizes bulk material properties for a known set of coupon data defined in JSON format.')

if __name__ == '__main__':
    main()
