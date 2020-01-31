import json
import pywim
import vtk
import numpy as np
from numpy import linalg
import enum
from typing import List

class MaterialType(enum.Enum):
    Empty = -1
    Unknown = 0
    Skin = 1
    Wall = 2
    Infill = 3

def compute_max_principal_strain(strain_vector):
    
    strain_matrix = np.array( [ [strain_vector[0], 0.5 * strain_vector[3], 0.5 * strain_vector[4]],
                                [0.5 * strain_vector[3], strain_vector[1], 0.5 * strain_vector[5]],
                                [0.5 * strain_vector[4], 0.5 * strain_vector[5], strain_vector[2]] ] )
    e_vals, e_vecs = linalg.eig(strain_matrix)
    
    return np.max( [ np.abs(e) for e in e_vals ] )

class ElemGPEntry:
    def __init__(self, elid, gpid, data):
        self.elid = elid
        self.gpid = gpid
        self.data = data

    def data_to_scalar(self, result_name : str):
        if len(self.data) == 1:
            return self.data

        elif len(self.data) == 6 and result_name == 'strain':
            # only dealing with strain for now
            return compute_max_principal_strain(self.data)
                
        else:
            raise Exception('Unsupported data type for region results at gauss point.')

class RegionStats:
    '''
    Given a list of gp info by element, compute and store the requested stats.
    '''
    def __init__(self, elem_gp_list : List[ElemGPEntry], result_name : str):
        self.elem_gp_list = elem_gp_list

        if len(elem_gp_list) > 0:
            data = np.zeros((len(elem_gp_list), 1))

            for i in range(len(elem_gp_list)):
                data[i] = self.elem_gp_list[i].data_to_scalar(result_name)

            self.min = np.min(data)
            self.max = np.max(data)
            self.mean = np.mean(data)

            # Other stats could be computed as needed. 
            # For example, if we want to measure skewness.
            # self.median = np.median(data)
            # self.quart25 = np.percentile(data, 25)
            # self.quart75 = np.percentile(data, 75)

class ElementStats:
    '''
    Class that stores the stats for each region by element in a list. Used to populate the array for the vtk grid.
    '''
    def __init__(self, elem_reg_list):
        self.elem_reg_list = elem_reg_list

class ElementRegionResult:
    '''
    For a given element, this class stores the corresponding region stats.
    '''
    def __init__(self, eid, result_name, walls, skin, infill):
        self.eid = eid
        self.result_name = result_name
        self.walls = RegionStats(walls, result_name)
        self.skin = RegionStats(skin, result_name)
        self.infill = RegionStats(infill, result_name)

class RegionResult:
    '''
    Class that stores list of the gp data by region type. Calling element_stats then returns an ElementStatsHandler object containing the stats
    for each region by element.
    '''
    def __init__(self, result_name, size, nels, walls, skin, infill):
        self.name = result_name
        self.size = size
        self.nels = nels
        self.walls = walls
        self.skin = skin
        self.infill = infill

    def element_stats(self):
        '''
        Return the region statistics by element.
        '''
        elem_reg_list = []

        for eid in range(1, self.nels + 1):

            id_match = lambda p: p.elid == eid
            matching_items = lambda a: list(filter(id_match, a))
        
            elem_reg = ElementRegionResult(
                eid=eid,
                result_name=self.name,
                walls=matching_items(self.walls),
                skin=matching_items(self.skin),
                infill=matching_items(self.infill)
            )

            elem_reg_list.append(elem_reg)

        return ElementStats(elem_reg_list)

def region_filter(mat_type : List[pywim.fea.result.ResultMult], res : List[pywim.fea.result.ResultMult]):
    '''
    Given the material_type gauss point results, sort the given generic gauss point results (res) by region using the Region Handler.
    '''
    # Build two dictionaries of element Id to index for quicker searching
    eid2index = {}
    mat_eid2index = {}

    for i in range(len(res.values)):
        eid2index[res.values[i].id] = i
        mat_eid2index[mat_type.values[i].id] = i

    walls = []
    skin = []
    infill = []

    for eid in eid2index.keys():
        # Get gp results using element eid
        elv = res.values[ eid2index[eid] ]

        # Get gp material type using element eid
        mat_elv = mat_type.values[ mat_eid2index[eid] ]

        if elv.id != eid:
            print('Element id mismatch (result): {} != {}'.format(eid, elv.id))

        if mat_elv.id != eid:
            print('Element id mismatch (material type): {} != {}'.format(eid, mat_elv.id))

        ngps = len(mat_elv.values)

        for i in range(ngps):

            material_type_at_gp = mat_elv.values[i]
            result_at_gp = elv.values[i]

            if material_type_at_gp.id != result_at_gp.id:
                print('Gauss Point id mismatch in element {}: {} != {}'.format(eid, material_type_at_gp.id, result_at_gp.id))

            if MaterialType( int(material_type_at_gp.data[0]) ) == MaterialType.Wall:
                walls.append( ElemGPEntry( eid, result_at_gp.id, result_at_gp.data ) )

            elif MaterialType( int(material_type_at_gp.data[0]) ) == MaterialType.Skin:
                skin.append( ElemGPEntry( eid, result_at_gp.id, result_at_gp.data ) )

            elif MaterialType( int(material_type_at_gp.data[0]) ) == MaterialType.Infill:
                infill.append( ElemGPEntry( eid, result_at_gp.id, result_at_gp.data ) )

    return RegionResult(
        result_name=res.name,
        size=res.size,
        nels=len(mat_type.values),
        walls=walls,
        skin=skin,
        infill=infill
    )

def from_grid(dgrid):
    nodes = dgrid['nodes']
    elems = dgrid['elements']

    points = vtk.vtkPoints()
    points.SetNumberOfPoints(len(nodes))
    for n in nodes:
        points.SetPoint(n[0]-1, n[1], n[2], n[3])

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)

    for g in elems:
        dim = g['dimension']
        etype = g['type']
        eshape = g['numnodes']
        for c in g['connectivity']:
            if dim == 3 and etype == 'solid':
                if eshape == 8:
                    e = vtk.vtkHexahedron()
                elif eshape == 6:
                    e = vtk.vtkWedge()
            elif dim == 2 and etype == 'solid':
                e = vtk.vtkQuad()
            ids = e.GetPointIds()
            i = 0
            for nid in c[1:]:
                ids.SetId(i, nid-1)
                i += 1
            grid.InsertNextCell(e.GetCellType(), ids)

    return grid

def from_fea(mesh, inc, outputs):
    points = vtk.vtkPoints()
    points.SetNumberOfPoints(len(mesh.nodes))
    for n in mesh.nodes:
        points.SetPoint(n.id-1, n.x, n.y, n.z)

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)

    nels = 0
    for g in mesh.elements:
        for c in g.connectivity:
            if g.type == 'HEXL8' or g.type == 'VOXL':
                e = vtk.vtkHexahedron()
            elif g.type == 'TETL4':
                e = vtk.vtkTetra()
            elif g.type == 'WEDL6':
                e = vtk.vtkWedge()
            elif g.type == 'PSL4':
                e = vtk.vtkQuad()
            elif g.type == 'PSL3':
                e = vtk.vtkTriangle()
            elif g.type == 'PSQ6':
                e = vtk.vtkQuadraticTriangle()
            ids = e.GetPointIds()
            i = 0
            for nid in c.nodes:
                ids.SetId(i, nid-1)
                i += 1
            grid.InsertNextCell(e.GetCellType(), ids)
            nels += 1

    celldata = grid.GetCellData()
    pointdata = grid.GetPointData()

    def add_node_results(res : List[pywim.fea.result.Result]):
        array = vtk.vtkFloatArray()
        array.SetName(res.name)
        array.SetNumberOfComponents(res.size)

        for v in res.values:
            if res.size == 1:
                array.InsertNextTuple1(v.data[0])
            elif res.size == 3:
                array.InsertNextTuple3(v.data[0], v.data[1], v.data[2])
            elif res.size == 6:
                array.InsertNextTuple6(v.data[0], v.data[1], v.data[2], v.data[3], v.data[5], v.data[4])

        pointdata.AddArray(array)

    def add_gp_results(res : List[pywim.fea.result.ResultMult]):

        ngps = 1
        for v in res.values:
            ngps = max(ngps, len(v.values))
        
        # Build a dictionary of element Id to index for quicker searching
        eid2index = {}
        index = 0
        nlayers = 0
        nsectpts = 0
        nonlay_ngps = 0
        for v in res.values:
            eid2index[v.id] = index
            index += 1

            if v.values[0].layer == 0:
                nonlay_ngps = max(nonlay_ngps, len(v.values))
            else:
                nlayers = max(nlayers, max([sv.layer for sv in v.values]))
                nsectpts = max(nsectpts, max([sv.section_point for sv in v.values]))

        lay_gp_iter = None
        nonlay_gp_iter = list(range(nonlay_ngps))
        if nlayers > 0:
            ngps = int(round(ngps / (nlayers * nsectpts)))
            lay_gp_iter = []
            for l in range(nlayers):
                for k in range(nsectpts):
                    for g in range(ngps):
                        lay_gp_iter.append((l, k, g))

        # This is a severe limitation right now:
        # For layered data we are assuming all elements have the same number of
        # layers and section points, but we do check each element for total # gauss
        # pts to handle differences (e.g. WEDL6 vs HEXL8)
        def get_gauss_point_data(layered_output, elv, gpid):

            if not layered_output:
                g = gpid
                g_out_of_range = elv.values[0].layer > 0
            else:
                this_ngps = int( round(len(elv.values) / (nlayers * nsectpts)) )
                g = this_ngps * (gpid[0] * nsectpts + gpid[1]) + gpid[2]
                g_out_of_range = gpid[2] >= this_ngps or elv.values[0].layer == 0

            if len(elv.values) < (g + 1) or g_out_of_range:
                return [0., 0., 0., 0., 0., 0.]
            else:
                return elv.values[g].data

        for gp_iter in (nonlay_gp_iter, lay_gp_iter):
            if gp_iter is None:
                continue
            for gp in gp_iter:
                if type(gp) is int:
                    layered_output = False
                    out_name = '{}_G{}'.format(r.name, gp + 1)
                else:
                    layered_output = True
                    out_name = '{}_L{}_K{}_G{}'.format(res.name, gp[0] + 1, gp[1] + 1, gp[2] + 1)

                array = vtk.vtkFloatArray()
                array.SetName(out_name)
                array.SetNumberOfComponents(r.size)

                for eid in range(1, nels + 1):
                    elv = res.values[ eid2index[eid] ]

                    if elv.id != eid:
                        print('Element id mismatch: {} != {}'.format(eid, elv.id))

                    gpdata = get_gauss_point_data(layered_output, elv, gp)

                    # last two vals intentionally swapped because VTU ordering is XX, YY, ZZ, XY, YZ, XZ
                    if res.size == 1:
                        array.InsertNextTuple1(gpdata[0])
                    elif res.size == 3:
                        array.InsertNextTuple3(gpdata[0], gpdata[1], gpdata[2])
                    elif res.size == 6:
                        array.InsertNextTuple6(gpdata[0], gpdata[1], gpdata[2], gpdata[3], gpdata[5], gpdata[4])

                celldata.AddArray(array)

    def add_elem_results(res : List[pywim.fea.result.Result]):
        array = vtk.vtkFloatArray()
        array.SetName(res.name)
        array.SetNumberOfComponents(res.size)

        for e in res.values:
            if res.size == 1:
                array.InsertNextTuple1(e.data[0])
            elif res.size == 3:
                array.InsertNextTuple3(e.data[0], e.data[1], e.data[2])
            elif res.size == 6:
                array.InsertNextTuple6(e.data[0], e.data[1], e.data[2], e.data[3], e.data[5], e.data[4])

        celldata.AddArray(array)

    def add_region_results_by_element(reg_result : RegionResult):

        elem_stats = reg_result.element_stats()

        wall_array = vtk.vtkFloatArray()
        wall_array.SetName('{}_wall'.format(reg_result.name))
        wall_array.SetNumberOfComponents(3)

        skin_array = vtk.vtkFloatArray()
        skin_array.SetName('{}_skin'.format(reg_result.name))
        skin_array.SetNumberOfComponents(3)

        infill_array = vtk.vtkFloatArray()
        infill_array.SetName('{}_infill'.format(reg_result.name))
        infill_array.SetNumberOfComponents(3)

        for e in elem_stats.elem_reg_list:
            if e.walls.elem_gp_list != []:
                wall_array.InsertNextTuple3(e.walls.min, e.walls.mean, e.walls.max)
            else:
                wall_array.InsertNextTuple3(float('NaN'), float('NaN'), float('NaN'))

            if e.skin.elem_gp_list != []:
                skin_array.InsertNextTuple3(e.skin.min, e.skin.mean, e.skin.max)
            else:
                skin_array.InsertNextTuple3(float('NaN'), float('NaN'), float('NaN'))

            if e.infill.elem_gp_list != []:
                infill_array.InsertNextTuple3(e.infill.min, e.infill.mean, e.infill.max)
            else:
                infill_array.InsertNextTuple3(float('NaN'), float('NaN'), float('NaN'))

        celldata.AddArray(wall_array)
        celldata.AddArray(skin_array)
        celldata.AddArray(infill_array)

    if 'node' in outputs:
        for res in inc.node_results:
            print('\tTranslating {} Node Result'.format(res.name))
            add_node_results(res)

    if 'element' in outputs:
        for res in inc.element_results:
            print('\tTranslating {} Element Result'.format(res.name))
            add_elem_results(res)

    '''
    For now, region specific results are restricted to gauss point data.
    '''
    if 'region' in outputs:
        try:
            mat_type = inc.gauss_point_results['material_type']
        except StopIteration:
            raise Exception('No material_type information at the gauss points exists. Unable to detect regions.')

        for res in inc.gauss_point_results:

            if res.name == 'material_type':
                continue
            else:
                reg_result = region_filter(mat_type, res)

                print('\tTranslating {} Region Result By Element'.format(res.name))
                add_region_results_by_element(reg_result)
    
    if 'gauss_point' in outputs:
        for res in inc.gauss_point_results:

            if res.name == 'material_type':
                continue
            else:
                print('\tTranslating {} Gauss Point Result'.format(res.name))
                add_gp_results(res)

    return grid

def grid_to_vtu(name, dmdl):
    gridw = vtk.vtkXMLUnstructuredGridWriter()
    gridw.SetFileName('{}.vtu'.format(name))

    grid = from_grid(dmdl)

    gridw.SetInputData(grid)
    gridw.Write()

def wim_result_to_vtu(db, name='temp', outputs=None):
    '''
    db is the fea result database object. outputs is a list of result outputs that will be included in the vtu file.
    '''
    mesh = db.mesh

    if outputs == None:
        outputs = ['node', 'element'] # Default to node and element results

    for step in db.steps:
        print(step.name)

        gridw = vtk.vtkXMLUnstructuredGridWriter()
        gridw.SetFileName('{}-{}.vtu'.format(name, step.name))

        inc = step.increments[-1]
        grid = from_fea(mesh, inc, outputs)

        gridw.SetInputData(grid)
        gridw.Write()
