import os
import sys
import json
import pywim

def main():
    if len(sys.argv) < 2:
        usage()
        return

    jmdl = sys.argv[1]

    with open(jmdl, 'r') as fjmdl:
        dmdl = json.load(fjmdl)

    if jmdl.endswith('.grid'):
        grid_to_vtu(jmdl, dmdl)
    elif jmdl.endswith('.json'):
        jrst = f'{jmdl}.rst'

        mdl = pywim.ModelEncoder.dict_to_object(dmdl, pywim.model.Model)

        if os.path.exists(jrst):
            with open(jrst, 'r') as fjrst:
                drdb = json.load(fjrst)
        
            db = pywim.ModelEncoder.dict_to_object(drdb, pywim.result.Database)

        wim_result_to_vtu(jmdl, mdl, db)

def usage():
    print('Usage:')
    print(f'{sys.argv[0]} JSON')
    print('If JSON file ends with .json it is assumed to be a wim FEA model, if it ends with .grid it is assumed a wim Grid definition')

if __name__ == '__main__':
    main()
