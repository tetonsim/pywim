import json
import pywim
import vtk
import numpy as np
from numpy import linalg
import enum

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

    def data_to_scalar(self):
        if len(self.data) == 1:
            return self.data
        elif len(self.data) == 3:
            # stress
            pass
        elif len(self.data) == 6:
            # strain
            return compute_max_principal_strain(self.data)
        else:
            raise Exception('Unknown data type at gauss point.')

class RegionStats:
    def __init__(self, reg_list : pywim.WimList(ElemGPEntry)):
        self.reg_list = reg_list
        self.min = None
        self.max = None
        self.median = None
        self.mean = None
        self.quart25 = None
        self.quart75 = None

    @property
    def num_gp_in_region(self):
        return len(self.reg_list)

    def populate_stats(self):
        data = np.zeros((self.num_gp_in_region, 1))

        for i in range(self.num_gp_in_region):
            data[i] = self.reg_list[i].data_to_scalar()

        self.min = np.min(data)
        self.max = np.max(data)
        self.median = np.median(data)
        self.mean = np.mean(data)
        self.quart25 = np.percentile(data, 25)
        self.quart75 = np.percentile(data, 75)

        return self

class ElementStatsHandler:
    def __init__(self):
        self.elem_reg_list = pywim.WimList(ElementRegionHandler)

class ElementRegionHandler:
    def __init__(self, eid):
        self.eid = eid
        self.walls = pywim.WimList(ElemGPEntry)
        self.walls_stats = None
        self.skin = pywim.WimList(ElemGPEntry)
        self.skin_stats = None
        self.infill = pywim.WimList(ElemGPEntry)
        self.infill_stats = None

    def get_element_region_stats(self):
        if len(self.walls) > 0:
            self.walls_stats = RegionStats(self.walls).populate_stats()

        if len(self.skin) > 0:
            self.skin_stats = RegionStats(self.skin).populate_stats()

        if len(self.infill) > 0:
            self.infill_stats = RegionStats(self.infill).populate_stats()

class RegionHandler:
    def __init__(self, name, size, nels):
        self.name = name
        self.size = size
        self.nels = nels
        self.walls = pywim.WimList(ElemGPEntry)
        self.skin = pywim.WimList(ElemGPEntry)
        self.infill = pywim.WimList(ElemGPEntry)

    def element_results(self):
        '''
        Return the region statistics by element.
        '''
        elem_stats = ElementStatsHandler()

        for eid in range(1, self.nels + 1):
            elem_reg = ElementRegionHandler(eid)

            for w in self.walls:
                if w.elid == eid:
                    elem_reg.walls.append(w)

            for s in self.skin:
                if s.elid == eid:
                    elem_reg.skin.append(s)

            for i in self.infill:
                if i.elid == eid:
                    elem_reg.infill.append(i)

            elem_reg.get_element_region_stats()
            elem_stats.elem_reg_list.append(elem_reg)

        return elem_stats

def region_filter(mat_type, r):
    '''
    Given the material_type gauss point results, sort the given generic gauss point results (r) by region using the ElementRegion Handler.
    '''
    # Build two dictionaries of element Id to index for quicker searching
    eid2index = {}
    mat_eid2index = {}
    index = 0

    for i in range(len(r.values)):
        eid2index[r.values[i].id] = index
        mat_eid2index[mat_type.values[i].id] = index
        index += 1

    nels = len(mat_type.values)

    reg_handler = RegionHandler(r.name, r.size, nels)

    for eid in range(1, nels + 1):
        # Get gp results using element eid
        elv = r.values[ eid2index[eid] ]

        # Get gp material type using element eid
        mat_elv = mat_type.values[ mat_eid2index[eid] ]

        if elv.id != eid:
            print('Element id mismatch (result): {} != {}'.format(eid, elv.id))

        if mat_elv.id != eid:
            print('Element id mismatch (material type): {} != {}'.format(eid, mat_elv.id))

        ngps = len(mat_elv.values)

        for i in range(ngps):

            if mat_elv.values[i].id != elv.values[i].id:
                print('Gauss Point id mismatch in element {}: {} != {}'.format(eid, mat_elv.values[i].id, elv.values[i].id))

            if MaterialType( int(mat_elv.values[i].data[0]) ) == MaterialType.Wall:
                reg_handler.walls.append( ElemGPEntry( eid, elv.values[i].id, elv.values[i].data ) )

            elif MaterialType( int(mat_elv.values[i].data[0]) ) == MaterialType.Skin:
                reg_handler.skin.append( ElemGPEntry( eid, elv.values[i].id, elv.values[i].data ) )

            elif MaterialType( int(mat_elv.values[i].data[0]) ) == MaterialType.Infill:
                reg_handler.infill.append( ElemGPEntry( eid, elv.values[i].id, elv.values[i].data ) )

    print(f'Region info by GP: {len(reg_handler.walls)} wall gp, {len(reg_handler.skin)} skin gp, {len(reg_handler.infill)} infill gp,')

    return reg_handler


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

    def add_node_results(r):
        array = vtk.vtkFloatArray()
        array.SetName(r.name)
        array.SetNumberOfComponents(r.size)

        for v in r.values:
            if r.size == 1:
                array.InsertNextTuple1(v.data[0])
            elif r.size == 3:
                array.InsertNextTuple3(v.data[0], v.data[1], v.data[2])
            elif r.size == 6:
                array.InsertNextTuple6(v.data[0], v.data[1], v.data[2], v.data[3], v.data[5], v.data[4])

        pointdata.AddArray(array)

    def add_gp_results(r):

        ngps = 1
        for v in r.values:
            ngps = max(ngps, len(v.values))
        
        # Build a dictionary of element Id to index for quicker searching
        eid2index = {}
        index = 0
        nlayers = 0
        nsectpts = 0
        nonlay_ngps = 0
        for v in r.values:
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
                    out_name = '{}_L{}_K{}_G{}'.format(r.name, gp[0] + 1, gp[1] + 1, gp[2] + 1)

                array = vtk.vtkFloatArray()
                array.SetName(out_name)
                array.SetNumberOfComponents(r.size)

                for eid in range(1, nels + 1):
                    elv = r.values[ eid2index[eid] ]

                    if elv.id != eid:
                        print('Element id mismatch: {} != {}'.format(eid, elv.id))

                    gpdata = get_gauss_point_data(layered_output, elv, gp)

                    # last two vals intentionally swapped because VTU ordering is XX, YY, ZZ, XY, YZ, XZ
                    if r.size == 1:
                        array.InsertNextTuple1(gpdata[0])
                    elif r.size == 3:
                        array.InsertNextTuple3(gpdata[0], gpdata[1], gpdata[2])
                    elif r.size == 6:
                        array.InsertNextTuple6(gpdata[0], gpdata[1], gpdata[2], gpdata[3], gpdata[5], gpdata[4])

                celldata.AddArray(array)

    def add_elem_results(r):
        array = vtk.vtkFloatArray()
        array.SetName(r.name)
        array.SetNumberOfComponents(r.size)

        for e in r.values:
            if r.size == 1:
                array.InsertNextTuple1(e.data[0])
            elif r.size == 3:
                array.InsertNextTuple3(e.data[0], e.data[1], e.data[2])
            elif r.size == 6:
                array.InsertNextTuple6(e.data[0], e.data[1], e.data[2], e.data[3], e.data[5], e.data[4])

        celldata.AddArray(array)

    def add_region_results_by_element(reg_handler : RegionHandler):

        elem_stats = reg_handler.element_results()

        wall_array = vtk.vtkFloatArray()
        wall_array.SetName('{}_wall'.format(reg_handler.name))
        wall_array.SetNumberOfComponents(3)

        skin_array = vtk.vtkFloatArray()
        skin_array.SetName('{}_skin'.format(reg_handler.name))
        skin_array.SetNumberOfComponents(3)

        infill_array = vtk.vtkFloatArray()
        infill_array.SetName('{}_infill'.format(reg_handler.name))
        infill_array.SetNumberOfComponents(3)

        for e in elem_stats.elem_reg_list:
            if e.walls_stats:
                wall_array.InsertNextTuple3(e.walls_stats.min, e.walls_stats.mean, e.walls_stats.max)
            else:
                wall_array.InsertNextTuple3(0, 0, 0)

            if e.skin_stats:
                skin_array.InsertNextTuple3(e.skin_stats.min, e.skin_stats.mean, e.skin_stats.max)
            else:
                skin_array.InsertNextTuple3(0, 0, 0)

            if e.infill_stats:
                infill_array.InsertNextTuple3(e.infill_stats.min, e.infill_stats.mean, e.infill_stats.max)
            else:
                infill_array.InsertNextTuple3(0, 0, 0)

        celldata.AddArray(wall_array)
        celldata.AddArray(skin_array)
        celldata.AddArray(infill_array)

    if 'node' in outputs:
        for r in inc.node_results:
            print('\tTranslating {} Node Result'.format(r.name))
            add_node_results(r)

    if 'element' in outputs:
        for r in inc.element_results:
            print('\tTranslating {} Element Result'.format(r.name))
            add_elem_results(r)

    '''
    For now, region specific results are restricted to gauss point data.
    '''
    if 'region' in outputs:
        try:
            mat_type = inc.gauss_point_results['material_type']
        except StopIteration:
            raise Exception('No material_type information at the gauss points exists. Unable to detect regions.')

        for r in inc.gauss_point_results:

            if r.name == 'material_type':
                continue
            else:
                reg_handler = region_filter(mat_type, r)

                print('\tTranslating {} Region Result By Element'.format(r.name))
                add_region_results_by_element(reg_handler)
    
    if 'gauss_point' in outputs:
        for r in inc.gauss_point_results:

            if r.name == 'MaterialType':
                continue
            else:
                print('\tTranslating {} Gauss Point Result'.format(r.name))
                add_gp_results(r)

    return grid

def grid_to_vtu(name, dmdl):
    gridw = vtk.vtkXMLUnstructuredGridWriter()
    gridw.SetFileName('{}.vtu'.format(name))

    grid = from_grid(dmdl)

    gridw.SetInputData(grid)
    gridw.Write()

def wim_result_to_vtu(db, name=None, outputs=None):
    '''
    db is the fea result database object. outputs is a list of result outputs that will be included in the vtu file.
    '''
    mesh = db.mesh

    if name == None:
        name = 'temp'

    if outputs == None:
        outputs = ['node', 'element', 'region'] # Default to node, element results and region results

    for step in db.steps:
        print(step.name)

        gridw = vtk.vtkXMLUnstructuredGridWriter()
        gridw.SetFileName('{}-{}.vtu'.format(name, step.name))

        inc = step.increments[-1]
        grid = from_fea(mesh, inc, outputs)

        gridw.SetInputData(grid)
        gridw.Write()
