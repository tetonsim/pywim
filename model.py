from . import ModelEncoder, WimObject, WimList, WimTuple, Meta

class Node(WimObject):
    def __init__(self, id, x, y, z=0.):
        self.id = id
        self.x = x
        self.y = y
        self.z = z
    
    @classmethod
    def __from_dict__(cls, d):
        return cls(d[0], d[1], d[2], d[3] if len(d) >= 4 else 0.)

    def __json__(self):
        return [self.id, self.x, self.y, self.z]

class Element(WimObject):
    def __init__(self, id, nodes=None):
        self.id = id
        self.nodes = nodes or []

    @classmethod
    def __from_dict__(cls, d):
        return cls(d[0], d[1:])

    def __json__(self):
        return [self.id, *self.nodes]

class ElementGroup(WimObject):
    def __init__(self, type='PSL4', thickness=1.0):
        self.type = type
        self.thickness = thickness
        self.connectivity = WimList(Element)

    @classmethod
    def __from_dict__(cls, d):
        egroup = cls(d['type'], d.get('thickness', 1.0))
        egroup.connectivity = ModelEncoder.dict_to_object(d['connectivity'], egroup.connectivity)
        return egroup

class Mesh(WimObject):
    def __init__(self):
        self.nodes = WimList(Node)
        self.elements = WimList(ElementGroup)

    @classmethod
    def __from_dict__(cls, d):
        mesh = cls()
        mesh.nodes = ModelEncoder.dict_to_object(d['nodes'], mesh.nodes)
        mesh.elements = ModelEncoder.dict_to_object(d['elements'], mesh.elements)
        return mesh

class NodeSet(WimObject):
    def __init__(self, name, nodes=None):
        self.name = name
        self.nodes = WimList(int)
        if nodes:
            for n in nodes:
                if isinstance(n, Node):
                    self.nodes.append(n.id)
                else:
                    self.nodes.append(n)

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['nodes'])

class ElementSet(WimObject):
    def __init__(self, name, elements=None):
        self.name = name
        self.elements = WimList(int)
        if elements:
            for e in elements:
                if isinstance(e, Element):
                    self.elements.append(e.id)
                else:
                    self.elements.append(e)

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['elements'])

class ElementFaces(WimObject):
    def __init__(self, face, elements=None):
        self.face = face
        self.elements = WimList(int)
        if elements:
            for e in elements:
                if isinstance(e, Element):
                    self.elements.append(e.id)
                else:
                    self.elements.append(e)

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['face'], d['elements'])

class SurfaceSet(WimObject):
    def __init__(self, name, faces=None):
        self.name = name
        self.faces = WimList(ElementFaces)
        if faces:
            self.faces.extend(faces)

    @classmethod
    def __from_dict__(cls, d):
        sset = cls(d['name'])
        sset.faces = ModelEncoder.dict_to_object(d['faces'], sset.faces)
        return sset

class Regions(WimObject):
    def __init__(self):
        self.node_sets = WimList(NodeSet)
        self.element_sets = WimList(ElementSet)
        self.surface_sets = WimList(SurfaceSet)

    @classmethod
    def __from_dict__(cls, d):
        reg = cls()
        reg.node_sets = ModelEncoder.dict_to_object(d['node_sets'], reg.node_sets)
        reg.element_sets = ModelEncoder.dict_to_object(d['element_sets'], reg.element_sets)
        reg.surface_sets = ModelEncoder.dict_to_object(d.get('surface_sets', []), reg.surface_sets)
        return reg

class Elastic(WimObject):
    def __init__(self, type='isotropic', properties=None, iso_plane=None):
        self.type = type
        self.iso_plane = iso_plane
        if properties:
            for p, v in properties.items():
                self.__dict__[p] = v

    @classmethod
    def __from_dict__(cls, d):
        elas_type = d.pop('type', 'isotropic')
        iso_plane = d.pop('iso_plane', None)
        return cls(elas_type, d, iso_plane)

class Expansion(WimObject):
    def __init__(self, type='isotropic', properties=None):
        self.type = type
        if properties:
            for p, v in properties.items():
                self.__dict__[p] = v

    @classmethod
    def __from_dict__(cls, d):
        elas_type = d.pop('type')
        return cls(elas_type, d)

class Material(WimObject):
    def __init__(self, name):
        self.name = name
        self.elastic = Elastic()
        #self.expansion = Expansion()

    @classmethod
    def __from_dict__(cls, d):
        m = cls(d['name'])
        m.elastic = ModelEncoder.dict_to_object(d.get('elastic', {}), m.elastic)
        #m.expansion = ModelEncoder.dict_to_object(d.get('expansion', {}), m.expansion)
        return m

class CoordinateSystem(WimObject):
    def __init__(self, name, xaxis=(1., 0., 0.), xyplane=(0., 1., 0.), origin=(0., 0., 0.)):
        self.name = name
        self.type = 'three_points'
        self.origin = origin
        self.xaxis = xaxis
        self.xyplane = xyplane

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['xaxis'], d['xyplane'], d['origin'])

class Section(WimObject):
    def __init__(self, name, material, csys=None):
        self.name = name
        self.material = material
        if csys:
            self.csys = csys

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['material'], d.get('csys'))

class SectionAssignment(WimObject):
    def __init__(self, name, section, elset):
        self.name = name
        self.section = section
        self.element_set = elset.name if isinstance(elset, ElementSet) else elset

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['section'], d['element_set'])

class BoundaryCondition(WimObject):
    def __init__(self, name, node_set, displacements=None):
        self.name = name
        self.node_set = node_set.name if isinstance(node_set, NodeSet) else node_set
        self.displacements = WimList(WimTuple.make(int, float))
        if displacements:
            self.displacements.extend(displacements)

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['node_set'], d['displacements'])

class ConcentratedForce(WimObject):
    def __init__(self, name, node_set, force=None):
        self.name = name
        self.node_set = node_set.name if isinstance(node_set, NodeSet) else node_set
        self.force = WimTuple(float, float, float)
        if force:
            self.force.set(force)

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['node_set'], d['force'])

class DistributedForce(WimObject):
    def __init__(self, name, surface_set, load_type):
        self.name = name
        self.surface_set = surface_set
        self.type = load_type

    @classmethod
    def __from_dict__(cls, d):
        name = d.get('name')
        sset = d.get('surface_set')
        dftype = d.get('type')

        if dftype == 'pressure':
            return Pressure(name, sset, d['pressure'])
        elif dftype == 'shear':
            return Shear(name, sset, 1., d['shear'])

        raise Exception('Unrecognized distributed force type %s' % dftype)

class Pressure(DistributedForce):
    def __init__(self, name, surface_set, pressure):
        super().__init__(name, surface_set, 'pressure')
        self.pressure = pressure

class Shear(DistributedForce):
    def __init__(self, name, surface_set, shear, vector):
        super().__init__(name, surface_set, 'shear')
        self.shear = WimTuple(float, float, float)
        self.shear.set( [shear * vector[0], shear * vector[1], shear * vector[2]] )

class NodeTemperature(WimObject):
    def __init__(self, name, node_set, temperature):
        self.name = name
        self.node_set = node_set.name if isinstance(node_set, NodeSet) else node_set
        self.temperature = temperature

    @classmethod
    def __from_dict__(cls, d):
        return cls(d['name'], d['node_set'], d['temperature'])

class ConstraintEquation(WimObject):
    def __init__(self, terms=None, constant=0.):
        self.terms = WimList(WimTuple.make(int, int, float))
        if terms:
            self.terms.extend(terms)
        self.constant = constant

    def add_term(self, node_id, dof, value):
        self.terms.append([node_id, dof, value])

    @classmethod
    def __from_dict__(cls, d):
        eq = cls(constant=d['constant'])
        eq.terms = ModelEncoder.dict_to_object(d['terms'], eq.terms)
        return eq

class Constraints(WimObject):
    def __init__(self):
        self.equations = WimList(ConstraintEquation)

    @classmethod
    def __from_dict__(cls, d):
        constraints = cls()
        constraints.equations = ModelEncoder.dict_to_object(d['equations'], constraints.equations)
        return constraints

class Step(WimObject):
    def __init__(self, name):
        self.name = name
        self.boundary_conditions = WimList(str)
        self.concentrated_forces = WimList(str)
        self.distributed_forces = WimList(str)
        self.node_temperatures = WimList(str)

    @classmethod
    def __from_dict__(cls, d):
        step = cls(d['name'])
        for ctype in ('boundary_conditions', 'concentrated_forces', 'distributed_forces', 'node_temperatures'):
            if ctype in d.keys():
                step.__dict__[ctype] = ModelEncoder.dict_to_object(d[ctype], step.__dict__[ctype])
        return step

class Model(WimObject):
    def __init__(self, name):
        self.name = name
        self.meta = Meta()
        self.mesh = Mesh()
        self.regions = Regions()
        self.materials = WimList(Material)
        self.csys = WimList(CoordinateSystem)
        self.sections = WimList(Section)
        self.section_assignments = WimList(SectionAssignment)
        self.boundary_conditions = WimList(BoundaryCondition)
        self.constraints = Constraints()
        self.concentrated_forces = WimList(ConcentratedForce)
        self.distributed_forces = WimList(DistributedForce)
        self.node_temperatures = WimList(NodeTemperature)
        self.steps = WimList(Step)
