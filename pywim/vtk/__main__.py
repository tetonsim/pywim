import os
import sys
import json
import pywim
from . import grid_to_vtu, wim_result_to_vtu

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

        mdl = pywim.fea.model.Model.from_dict(dmdl)

        if os.path.exists(jrst):
            with open(jrst, 'r') as fjrst:
                drdb = json.load(fjrst)
        
            db = pywim.fea.result.Database.from_dict(drdb)

        wim_result_to_vtu(mdl, db)
    elif jmdl.endswith('.json.rst'):
        db = pywim.fea.result.Database.from_dict(dmdl)
        mdl = pywim.fea.model.Model()
        mdl.mesh = db.mesh

        wim_result_to_vtu(mdl, db)

def usage():
    print('Usage:')
    print(f'{sys.argv[0]} JSON')
    print('If JSON file ends with .json it is assumed to be a wim FEA model, if it ends with .grid it is assumed a wim Grid definition')

if __name__ == '__main__':
    main()
