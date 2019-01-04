import json

VERSION = '0.2'

class WimObject(object):
    @classmethod
    def __from_dict__(cls, d):
        raise NotImplementedError('__from_dict__ not implemented in %s' % cls)

class WimList(list):
    def __init__(self, list_type):
        self.list_type = list_type

    def new(self):
        return WimList(self.list_type)

class WimTuple(list):
    def __init__(self, *types):
        self.types = types

    def new(self):
        return WimTuple(*self.types)

    def set(self, vals):
        assert len(vals) == len(self.types)
        for i in range(len(vals)):
            assert type(vals[i]) == self.types[i]
        self.clear()
        self.extend(vals)

    @staticmethod
    def make(*types):
        def __init__(self):
            self.types = types
        return type('_WimTuple', (WimTuple,), { '__init__': __init__ })

class Meta(WimObject):
    class Build(WimObject):
        def __init__(self):
            self.date = ''
            self.machine = ''
            self.hash = ''
            self.branch = ''

        @classmethod
        def __from_dict__(cls, d):
            b = cls()
            b.date = d.get('date', '')
            b.machine = d.get('machine', '')
            b.hash = d.get('hash', '')
            b.branch = d.get('branch', '')
            return b

    def __init__(self):
        self.version = VERSION
        self.build = Meta.Build()


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
        if obj is None:
            return None
        elif getattr(obj, '__json__', None):
            return obj.__json__()
        elif isinstance(obj, (int, float, str)):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [ ModelEncoder._obj_to_dict(v) for v in obj ]

        d = {}
        for k in obj.__dict__.keys():
            if k.startswith('_'):
                continue

            v = ModelEncoder._obj_to_dict(getattr(obj, k))

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

    @staticmethod
    def dict_to_object(d, obj):
        new_obj = None
        if isinstance(obj, WimList):
            new_obj = obj.new()
            for o in d:
                if obj.list_type in (int, float, str):
                    new_obj.append(o)
                elif issubclass(obj.list_type, WimTuple):
                    new_t = obj.list_type()
                    new_t.set(o)
                    new_obj.append(o) 
                elif issubclass(obj.list_type, WimObject):
                    new_obj.append(obj.list_type.__from_dict__(o))
                else:
                    raise Exception('Unsupported type for WimList deserialization: %s' % obj.list_type)
        elif isinstance(obj, WimTuple):
            new_obj = obj.new()
            new_obj.set(d)
        elif isinstance(obj, WimObject):
            #ModelEncoder._set_object_attrs(obj, d)
            new_obj = type(obj).__from_dict__(d)
        elif isinstance(obj, (int, float, str)):
            new_obj = d
        #elif isinstance(obj, (list, tuple)):
            #new_obj = list()
            #ModelEncoder._set_object_attrs(new_obj, d)
        #elif isinstance(obj, dict):
        #    pass
        else:
            raise Exception('Unsupported type for deserialization: %s' % type(obj))

        return new_obj

    @staticmethod
    def dict_to_model(d):
        from .model import Model
        mdl = Model(d.get('name', 'model'))
        ModelEncoder._set_object_attrs(mdl, d)
        return mdl

    @staticmethod
    def dict_to_results(d):
        from .result import Database
        db = Database()
        ModelEncoder._set_object_attrs(db, d)
        return db        

del json

from . import abaqus, model, result
