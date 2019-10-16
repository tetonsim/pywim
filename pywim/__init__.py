import json
import enum
import datetime
from warnings import warn

def _all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in _all_subclasses(c)])

class WimException(Exception):
    pass

class WimObject:
    @classmethod
    def from_dict(cls, d):
        return ModelEncoder.dict_to_object(d, cls())

    @classmethod
    def from_json(cls, j):
        return cls.from_dict(json.loads(j))

    @classmethod
    def model_from_file(cls, f):
        close_fp = False

        if isinstance(f, str):
            close_fp = True
            fp = open(f, 'r')
        else:
            fp = f
        
        dmodel = json.load(fp)

        if close_fp:
            fp.close()

        return ModelEncoder.dict_to_object(dmodel, cls())

    def to_dict(self):
        return ModelEncoder.object_to_dict(self)

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_json_file(self, f, indent=None):
        close_fp = False

        if isinstance(f, str):
            close_fp = True
            fp = open(f, 'w')
        else:
            fp = f

        json.dump(ModelEncoder.object_to_dict(self), fp, indent=indent)

        if close_fp:
            fp.close()

    def is_empty(self):
        '''
        Returns true if all attributes are None
        '''
        for k, v in self.__dict__.items():
            if v is not None:
                return False
        return True

class WimList(list):
    def __init__(self, list_type):
        self.list_type = list_type

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(key)
        elif isinstance(key, str):
            return next(o for o in self if o.name == key)
        raise TypeError('WimList key must be int or str')

    def new(self):
        return WimList(self.list_type)

    def add(self, val):
        if self.list_type == float and type(val) == int:
            val = float(val)
        assert type(val) == self.list_type, f'WimList incompatible type ({type(val)} != {self.list_type})'
        self.append(val)

    def names(self):
        return [o.name for o in self]

    def keys(self):
        return self.names()

    def is_empty(self):
        return len(self) == 0

class WimTuple(list):
    def __init__(self, *types):
        self.types = types

    def new(self):
        return WimTuple(*self.types)

    def set(self, vals):
        assert len(vals) == len(self.types), 'WimTuple incompatible lengths'
        for i in range(len(vals)):
            if self.types[i] == float and type(vals[i]) == int:
                vals[i] = float(vals[i])
            assert type(vals[i]) == self.types[i], f'WimTuple incompatible type ({type(vals[i])} != {self.types[i]})'
        self.clear()
        self.extend(vals)

    @staticmethod
    def make(*types):
        def __init__(self):
            self.types = types
        return type('_WimTuple', (WimTuple,), { '__init__': __init__ })

class WimIgnore:
    def __init__(self, object_type):
        self.type = object_type

    @staticmethod
    def make(object_type):
        def __init__(self, *args, **kwargs):
            WimIgnore.__init__(self, object_type)            
            object_type.__init__(self, *args, **kwargs)
        return type(f'_WimIgnore_{object_type.__name__}', (WimIgnore, object_type), { '__init__': __init__ })

class Meta(WimObject):
    class Build(WimObject):
        def __init__(self):
            self.date = ''
            self.machine = ''
            self.hash = ''
            self.branch = ''

        def populate(self):
            pass
            # TODO - is there anything here we want to grab during setup/distribution?

        @classmethod
        def __from_dict__(cls, d):
            b = cls()
            b.date = d.get('date', '')
            b.machine = d.get('machine', '')
            b.hash = d.get('hash', '')
            b.branch = d.get('branch', '')
            return b

    def __init__(self):
        self.version = None
        self.app = None
        self.date = None
        self.build = Meta.Build()

    def populate(self, app=None):
        self.version = '' # TODO, need to get this from somewhere that setup.py can also get it from
        self.app = app if app else 'pywim'
        self.date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.build.populate()

    @classmethod
    def __from_dict__(cls, d):
        m = Meta()
        m.version = d.get('version', '')
        m.build = ModelEncoder.dict_to_object(d.get('build', {}), m.build)

class ModelEncoder(json.JSONEncoder):
    def default(self, obj):
        return ModelEncoder._obj_to_dict(obj)

    @staticmethod
    def _obj_to_dict(obj):
        warn('_obj_to_dict deprecated, use object_to_dict', DeprecationWarning)
        return ModelEncoder.object_to_dict(obj)

    @staticmethod
    def object_to_dict(obj):
        if obj is None or (isinstance(obj, (WimObject, WimList)) and obj.is_empty()) or isinstance(obj, WimIgnore):
            return None
        elif getattr(obj, '__to_dict__', None):
            return obj.__to_dict__()
        elif getattr(obj, '__json__', None):
            warn(f'__json__ extension is deprecated, use __to_dict__: {type(obj)}', DeprecationWarning)
            return obj.__json__()
        elif isinstance(obj, (int, float, str)):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [ ModelEncoder.object_to_dict(v) for v in obj ]
        elif isinstance(obj, enum.Enum):
            return obj.name

        d = {}

        keys = obj.keys() if isinstance(obj, dict) else obj.__dict__.keys()

        if len(keys) == 0:
            return None
        
        for k in keys:
            if k.startswith('_'):
                continue

            v = ModelEncoder.object_to_dict(getattr(obj, k))

            if v is not None:
                d[k] = v

        return d

    @staticmethod
    def _set_object_attrs(obj, d):
        for k in obj.__dict__:
            v = getattr(obj, k)

            if k in d.keys():
                dv = d[k]

                newv = ModelEncoder.dict_to_object(dv, v)

                if newv is not None:
                    obj.__dict__[k] = newv
        return obj

    @staticmethod
    def _new_object_polymorphic(t, d):
        dtype = d.get('type')

        if dtype is None:
            dtype = getattr(t, 'DEFAULTTYPENAME', None)
        
        if dtype:
            subclasses = _all_subclasses(t)
            for c in subclasses:
                jtype = getattr(c, 'JSONTYPENAME', None)
                
                if jtype and jtype == dtype:
                    return c()

        return t()

    @staticmethod
    def dict_to_object(d, obj):
        if isinstance(obj, type):
            obj = obj()

        new_obj = None
        if isinstance(obj, WimList):
            new_obj = obj.new()
            for o in d:
                if obj.list_type in (int, float, str):
                    new_obj.add(o)
                elif issubclass(obj.list_type, WimTuple):
                    new_t = obj.list_type()
                    new_t.set(o)
                    new_obj.append(new_t) 
                elif issubclass(obj.list_type, WimObject):
                    if hasattr(obj.list_type, '__from_dict__'):
                        new_obj.append(obj.list_type.__from_dict__(o))
                    else:
                        #new_t = obj.list_type()
                        new_t = ModelEncoder._new_object_polymorphic(obj.list_type, o)
                        new_obj.append(ModelEncoder._set_object_attrs(new_t, o))
                else:
                    raise WimException(f'Unsupported type for WimList deserialization: {obj.list_type}')
        elif isinstance(obj, WimTuple):
            new_obj = obj.new()
            new_obj.set(d)
        elif isinstance(obj, WimObject):
            if hasattr(obj, '__from_dict__'):
                new_obj = type(obj).__from_dict__(d)
            else:
                #new_obj = type(obj)()
                new_obj = ModelEncoder._new_object_polymorphic(type(obj), d)
                ModelEncoder._set_object_attrs(new_obj, d)
        elif isinstance(obj, enum.Enum):
            new_obj = obj.__class__[d]
        elif isinstance(obj, (int, float, str, dict)) or obj is None:
            new_obj = d
        elif isinstance(obj, WimIgnore):
            new_obj = obj.__class__()
        else:
            raise WimException('Unsupported type for deserialization: %s' % type(obj))

        return new_obj

#del json

from . import abaqus, am, chop, job, micro, model, optimization, result, smartslice

