""" 
This script converts from pywim to odb.
It reads data from pywim model (.json) and results files (.rst)
and writes an Abaqus results file (.odb).

Usage: abaqus python wimfea_to_odb.py wim_filename

Requirements: 
1. wim input and output filenames must match
2. Abaqus must be installed

Supported features:
1. multiple steps
2. multiple increments
3. element types
    a. 8-node hex, full integration, non-layered
4. translated field outputs
    a. stress
    b. displacement

Future enchancements:
1. add support for layered 8-node hex
2. translate strains, failure index, etc. 
"""

import sys
import json
from abaqusConstants import *
from odbAccess import *

def translate_wim_files(wim_model_name):
    with open(wim_model_name + '.json', 'r') as f:
        wim_model = json.load(f)
    with open(wim_model_name + '.json.rst', 'r') as h:
        wim_result = json.load(h)

    odb = wim_to_odb(wim_model, wim_result, wim_model_name)
    odb.save()

def wim_to_odb(wim_model, wim_result, wim_model_name):
    odb = Odb(name=wim_model_name, path=wim_model_name + '_translated.odb')

    instance = _add_mesh_to_odb(wim_model, odb)
    
    _add_results_to_odb(wim_result, odb, instance)

    return odb

def _add_mesh_to_odb(wim_model, odb):
    json_nodes = wim_model['mesh']['nodes']
    json_elements = wim_model['mesh']['elements'][0]['connectivity']
    
    abq_nodes = tuple(tuple(x) for x in json_nodes)
    abq_elements = tuple(tuple(x) for x in json_elements)

    part = odb.Part(name='part-1', embeddedSpace=THREE_D, type=DEFORMABLE_BODY)

    part.addNodes(nodeData=abq_nodes, nodeSetName='all_nodes')
    part.addElements(elementData=abq_elements, type='C3D8', elementSetName='all_elements')

    instance = odb.rootAssembly.Instance(name='part-1-1', object=part)

    return instance

def _add_results_to_odb(wim_result, odb, instance):
    for wim_step in wim_result['steps']:
        _add_step_results_to_odb(wim_step, odb, instance)

def _add_step_results_to_odb(wim_step, odb, instance):
    odb_step = odb.Step(name=str(wim_step['name']), description='', domain=TIME, timePeriod=1.0)

    inc_num = 0
    for inc in wim_step['increments']:
        inc_num += 1
        _add_inc_results_to_odb_step(inc, odb_step, inc_num, instance)

def _add_inc_results_to_odb_step(inc, odb_step, inc_num, instance):
    odb_frame = odb_step.Frame(incrementNumber=inc_num, frameValue=1.0)

    # add displacements to odb_frame
    node_results = inc['node_results']

    disp_values = _get_result_by_name(node_results, 'displacement')['values']

    abq_node_labels = tuple(n['id'] for n in disp_values)
    abq_displacements = tuple(tuple(n['data']) for n in disp_values)

    disp_field = odb_frame.FieldOutput(name='U', description='Displacement', type=VECTOR, validInvariants=(MAGNITUDE,))
    disp_field.addData(position=NODAL, instance=instance, labels=abq_node_labels, data=abq_displacements)

    # add stresses to odb_frame
    gp_results = inc['gauss_point_results']

    stress_values = _get_result_by_name(gp_results, 'stress')['values']

    gp_stresses = []

    for e in stress_values:
        wim_values = [gp['data'] for gp in e['values']]
        abq_values = [
            wim_values[0],
            wim_values[4],
            wim_values[2],
            wim_values[6],
            wim_values[1],
            wim_values[5],
            wim_values[3],
            wim_values[7]
        ]
        gp_stresses.extend(abq_values)

    abq_element_labels = tuple(n['id'] for n in stress_values)
    abq_gp_stresses = tuple(tuple(x) for x in gp_stresses)

    stress_field = odb_frame.FieldOutput(name='S', description='Stress', type=TENSOR_3D_FULL, validInvariants=(MISES,))
    stress_field.addData(position=INTEGRATION_POINT, instance=instance, labels=abq_element_labels, data=abq_gp_stresses)

def _get_result_by_name(entity_results, result_name):
    result = None
    for r in entity_results:
        if r['name'] == result_name:
            result = r
            break

    if result is None:
        raise KeyError(result_name + ' result is missing')

    return result

def main():
    # add error message if user does not supply filename argument
    translate_wim_files(sys.argv[-1])

if __name__ == '__main__':
    main()