import time
import uuid
import threading
import collections

from .. import micro, model, mq, result, ModelEncoder

class Result:
    def __init__(self, success=False, result=None, thread=None):
        self.thread = thread
        self.success = success
        self.result = result

class Agent:
    def __init__(self, input_type, output_type, url, queue_produce=None, queue_consume=None):
        self.input_type = input_type
        self.output_type = output_type

        # Create a connection maker with default queue names
        self.mq = mq.ConnectionMaker(mq.SimpleConnection, url, queue_produce, queue_consume)

    @classmethod
    def FEA(cls, url, queue_produce=None, queue_consume=None):
        return cls(model.Model, result.Database, url, queue_produce, queue_consume)

    @classmethod
    def Micromechanics(cls, url, queue_produce=None, queue_consume=None):
        return cls(micro.Run, micro.Result, url, queue_produce, queue_consume)

    def run_sync(self, job_input):
        dinput = ModelEncoder.object_to_dict(job_input)
        
        connection = self.mq()
        rid = connection.publish(dinput)

        resp = None

        while resp is None:
            resp = connection.get(rid)

            if resp and resp['id'] != rid:
                # Not the Id we were looking for, reset resp to None and let that message die
                # TODO - this situation is complicated, and how its handled probably depends
                # on the specific producer/consumer relationship
                resp = None

            if resp is None:
                time.sleep(0.2)

        if len(resp['errors']) > 0:
            return Result()

        result = ModelEncoder.dict_to_object(resp['content'], self.output_type)

        return Result(True, result)

    def run(self, job_input):
        run_result = Result()
        
        def thread_func():
            r = self.run_sync(job_input)
            run_result.success = r.success
            run_result.result = r.result
        
        run_result.thread = threading.Thread(target=thread_func)
        
        return run_result
