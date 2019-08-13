import time
import uuid
import threading
import collections

from .. import micro, model, mq, result, ModelEncoder

class Result:
    def __init__(self, success=False, input=None, result=None, thread=None, errors=None):
        self.thread = thread
        self.success = success
        self.input = input
        self.result = result
        self.errors = errors

class Agent:
    def __init__(self, input_type, output_type, url, queue_produce=None, queue_consume=None):
        self.input_type = input_type
        self.output_type = output_type

        # Create a connection maker with default queue names
        self.mq = mq.ConnectionMaker(mq.DirectReplyConnection, url, queue_produce, queue_consume)

    @classmethod
    def FEA(cls, url, queue_produce=None, queue_consume=None):
        return cls(model.Model, result.Database, url, queue_produce, queue_consume)

    @classmethod
    def Micromechanics(cls, url, queue_produce=None, queue_consume=None):
        return cls(micro.Run, micro.Result, url, queue_produce, queue_consume)

    def run_sync(self, job_input):
        dinput = ModelEncoder.object_to_dict(job_input)
        
        conn = self.mq()
        conn.publish(dinput)

        resp = conn.get()

        if resp is None:
            return Result(False, errors=['Missing response'])

        if len(resp['errors']) > 0:
            return Result(resp['errors'])

        if resp['content'] is None:
            return Result(False, errors=['Missing response content'])

        result = ModelEncoder.dict_to_object(resp['content'], self.output_type)

        return Result(True, job_input, result)

    def run(self, job_input):
        run_result = Result()
        
        def thread_func():
            r = self.run_sync(job_input)
            run_result.success = r.success
            run_result.input = r.input
            run_result.result = r.result
        
        run_result.thread = threading.Thread(target=thread_func)
        
        return run_result
