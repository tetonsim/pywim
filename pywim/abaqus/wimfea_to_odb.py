""" 
This script reads data from pywim input (.json) and results files (.rst)
and writes an Abaqus results file (.odb). It converts from from pywim to odb.

Author: Rick Dalgarno
Date: 9/30/19
"""

import json

filename = 'two_sections' # this is the only variable to define


### get nodes and elements from JSON input file ###

with open(filename + '.json', 'r') as f:
    input = json.load(f)

json_nodes = input['mesh']['nodes']
json_elements = input['mesh']['elements'][0]['connectivity']

# convert a list-of-lists to a tuple-of-tuples
abq_nodes = tuple(tuple(x) for x in json_nodes)
abq_elements = tuple(tuple(x) for x in json_elements)


### get node labels and displacements from JSON results file ###

with open(filename + '.json.rst', 'r') as h:
    output = json.load(h)

node_results = output['steps'][0]['increments'][0]['node_results']

for x in node_results:
    if x['name'] == 'displacement':
        disp_values = x['values']

node_labels = []
node_displacements = []

for x in disp_values: # generate list of node labels and list of node displacements
    node_label = x['id']
    node_disp = tuple(x['data'])
    node_labels.append(node_label)
    node_displacements.append(node_disp)

abq_node_labels = tuple(node_labels)
abq_displacements = tuple(node_displacements)


### get element labels and gauss point stresses from JSON results file ###

gp_results = output['steps'][0]['increments'][0]['gauss_point_results']

for x in gp_results:
    if x['name'] == 'stress':
        stress_values = x['values']

element_labels = []
gp_stresses = []

for x in stress_values: # generate list of element labels
    element_label = x['id']
    element_labels.append(element_label)

for j in range(len(stress_values)):
    wim_values = {}
    abq_values = {}
    count = 0
    for y in stress_values[j]['values']: # reorder gauss point values
        count += 1
        wim_values[count] = y['data']
    abq_values[1] = wim_values[1]
    abq_values[2] = wim_values[5]
    abq_values[3] = wim_values[3]
    abq_values[4] = wim_values[7]
    abq_values[5] = wim_values[2]
    abq_values[6] = wim_values[6]
    abq_values[7] = wim_values[4]
    abq_values[8] = wim_values[8]
    for k in range(1, 9, 1): # add ordered gp values to gp list
        gp_stresses.append(abq_values[k])


abq_element_labels = tuple(element_labels)
abq_gp_stresses = tuple(tuple(x) for x in gp_stresses)


### Create an Abaqus odb file ###

from abaqusConstants import *
from odbAccess import *

odb = Odb(name=filename, path=filename + '_translated.odb')

# create the Model Data
part = odb.Part(name='part-1', embeddedSpace=THREE_D, type=DEFORMABLE_BODY)

part.addNodes(nodeData=abq_nodes, nodeSetName='all_nodes')
part.addElements(elementData=abq_elements, type='C3D8', elementSetName='all_elements')

a = odb.rootAssembly
instance = a.Instance(name='part-1-1', object=part)

# create the Results Data 
step = odb.Step(name='step-1', description='', domain=TIME, timePeriod=1.0)

frame = step.Frame(incrementNumber=1, frameValue=1.0)

# write displacements to the odb
disp_field = frame.FieldOutput(name='U', description='Displacement', type=VECTOR, validInvariants=(MAGNITUDE,))

disp_field.addData(position=NODAL, instance=instance, labels=abq_node_labels, data=abq_displacements)

# write the stress tensor to the odb
stress_field = frame.FieldOutput(name='S', description='Stress', type=TENSOR_3D_FULL, validInvariants=(MISES,))

stress_field.addData(position=INTEGRATION_POINT, instance=instance, labels=abq_element_labels, data=abq_gp_stresses)

odb.save()