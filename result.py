from . import ModelEncoder, WimObject, WimList, WimTuple

class ResultValue(WimObject):
    def __init__(self, id, data=None, sid=None):
        self.id = id
        self.sid = sid
        self.data = data if data else []

    @classmethod
    def __from_dict__(cls, d):
       return cls(d['id'], d['data']) 

class Result(WimObject):
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.values = WimList(ResultValue)

    @classmethod
    def __from_dict__(cls, d):
        rslt = cls(d['name'], d['size'])
        rslt.values = ModelEncoder.dict_to_object(d['values'], rslt.values)
        return rslt        

class ResultMult(Result):
    @classmethod
    def __from_dict__(cls, d):
        rslt = cls(d['name'], d['size'])
        for v in d['values']:
            pid = v['id']
            vals = WimList(ResultValue)
            for sv in v['values']:
                vals.append( ResultValue(pid, sv['data'], sv['id']) )
            rslt.values.extend(vals)
        return rslt

class Increment(WimObject):
    def __init__(self, time, dtime):
        self.time = time
        self.dtime = dtime
        self.node_results = WimList(Result)
        self.element_results = WimList(Result)
        self.gauss_point_results = WimList(ResultMult)

    @classmethod
    def __from_dict__(cls, d):
        inc = cls(d['time'], d['dtime'])
        inc.node_results = ModelEncoder.dict_to_object(d['node_results'], inc.node_results)
        inc.element_results = ModelEncoder.dict_to_object(d['element_results'], inc.element_results)
        inc.gauss_point_results = ModelEncoder.dict_to_object(d['gauss_point_results'], inc.gauss_point_results)
        return inc

class Step(WimObject):
    def __init__(self, name):
        self.name = name
        self.increments = WimList(Increment)

    @classmethod
    def __from_dict__(cls, d):
        step = cls(d['name'])
        step.increments = ModelEncoder.dict_to_object(d['increments'], step.increments)
        return step

class Database(WimObject):
    def __init__(self):
        self.steps = WimList(Step)

