from . import ModelEncoder, WimObject, WimList, WimTuple, Meta

class ResultValue(WimObject):
    def __init__(self, id, data=None, values=None):
        self.id = id
        self.data = data if data else []
        self.values = values if values else WimList(ResultValue)

    @classmethod
    def __from_dict__(cls, d):
       return cls(d['id'], d['data']) 

class Result(WimObject):
    def __init__(self, name=None, size=1):
        self.name = name if name else 'result'
        self.size = size
        self.values = WimList(ResultValue)

class ResultMult(Result):
    @classmethod
    def __from_dict__(cls, d):
        rslt = cls(d['name'], d['size'])
        for v in d['values']:
            pid = v['id']
            vals = WimList(ResultValue)
            subvals = WimList(ResultValue)
            for sv in v['values']:
                subvals.append(ResultValue(sv['id'], sv['data']))
            vals.append( ResultValue(pid, values=subvals) )
            rslt.values.extend(vals)
        return rslt

class Increment(WimObject):
    def __init__(self, time=0.0, dtime=1.0):
        self.time = time
        self.dtime = dtime
        self.node_results = WimList(Result)
        self.element_results = WimList(Result)
        self.gauss_point_results = WimList(ResultMult)

class Step(WimObject):
    def __init__(self, name=None):
        self.name = name if name else 'step'
        self.increments = WimList(Increment)

class Database(WimObject):
    def __init__(self):
        self.meta = Meta()
        self.steps = WimList(Step)

