import os
import sys
import json
from . import ExtrusionTest, Config, optimize_bulk

def main():
    if len(sys.argv) < 2:
        usage()
        return

    # Grab the configuration file if it exists
    if os.path.exists('opt.config'):
        oconfig = Config.model_from_file('opt.config')
    else:
        oconfig = Config()

    jopt = sys.argv[1]

    extrusion_test = ExtrusionTest.model_from_file(jopt)

    bulk_mat = optimize_bulk(extrusion_test, oconfig)
    bulk_mat.name = extrusion_test.name + '_bulk'

    bulk_mat.to_json_file(f'{jopt}.bulk', indent=1)

def usage():
    print('Usage:')
    print('{} JSON'.format(sys.argv[0]))
    print('Optimizes bulk material properties for a known set of coupon data defined in JSON format.')

if __name__ == '__main__':
    main()
