import json
import pywim
import vtk

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

def from_fea(mdl, inc):
    points = vtk.vtkPoints()
    points.SetNumberOfPoints(len(mdl.mesh.nodes))
    for n in mdl.mesh.nodes:
        points.SetPoint(n.id-1, n.x, n.y, n.z)

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)

    nels = 0
    for g in mdl.mesh.elements:
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
        #ngps = len( [v for v in r.values if v.id == 1] )
        #nels = round(len(r.values) / ngps)

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

                    #if len(elv.values) < (gp + 1):
                    #    gpdata = [0., 0., 0., 0., 0., 0.]
                    #else:
                    #    gpdata = elv.values[gp].data
                    
                    # last two vals intentionally swapped because VTU ordering is XX, YY, ZZ, XY, YZ, XZ
                    if r.size == 1:
                        array.InsertNextTuple1(gpdata[0])
                    elif r.size == 3:
                        array.InsertNextTuple3(gpdata[0], gpdata[1], gpdata[2])
                    elif r.size == 6:
                        array.InsertNextTuple6(gpdata[0], gpdata[1], gpdata[2], gpdata[3], gpdata[5], gpdata[4])

                celldata.AddArray(array)

    def add_elem_results(r):
        if not (r.size == 6 and r.name == 'orientation'):
            print('Unrecognized element result {}'.format(r.name))
            return

        array = vtk.vtkFloatArray()
        array.SetName(r.name)
        array.SetNumberOfComponents(r.size)

        for e in r.values:    
            if r.size == 6 and r.name == 'orientation':
                array.InsertNextTuple6(e.data[0], e.data[1], e.data[2], e.data[3], e.data[4], e.data[5])

        celldata.AddArray(array)

    for r in inc.node_results:
        print('\tTranslating {} Node Result'.format(r.name))
        add_node_results(r)

    for r in inc.gauss_point_results:
        print('\tTranslating {} Gauss Point Result'.format(r.name))
        add_gp_results(r)

    for r in inc.element_results:
        print('\tTranslating {} Element Result'.format(r.name))
        add_elem_results(r)

    return grid

def grid_to_vtu(name, dmdl):
    gridw = vtk.vtkXMLUnstructuredGridWriter()
    gridw.SetFileName('{}.vtu'.format(name))

    grid = from_grid(dmdl)

    gridw.SetInputData(grid)
    gridw.Write()

def wim_result_to_vtu(mdl, db):
    for step in db.steps:
        print(step.name)

        gridw = vtk.vtkXMLUnstructuredGridWriter()
        gridw.SetFileName('{}-{}.vtu'.format(mdl.name.replace(".json", ""), step.name))

        inc = step.increments[-1]
        grid = from_fea(mdl, inc)

        gridw.SetInputData(grid)
        gridw.Write()
