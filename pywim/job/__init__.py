import os
import sys
import shutil
import threading
import tempfile
import subprocess
import requests

from .. import micro, model, result, ModelEncoder

class Result:
    def __init__(self, success=False, input=None, result=None, thread=None, errors=None):
        self.thread = thread
        self.success = success
        self.input = input
        self.result = result
        self.errors = errors

class _Agent:
    def __init__(self, input_type, output_type):
        self.input_type = input_type
        self.output_type = output_type

    def run_sync(self, job_input):
        raise NotImplementedError()

    def run(self, job_input):
        raise NotImplementedError()

class FEACLIAgent(_Agent):
    def __init__(self, exe_name='wim-cli-json', exe_path=None):
        super().__init__(model.Model, result.Database)

        self.exe_name = exe_name
        self.exe_path = exe_path
        self.debug = False

    @property
    def _exe(self):
        if self.exe_path is None:
            return self.exe_name
        return os.path.join(self.exe_path, self.exe_name)

    def run_sync(self, job_input):
        dtmp = tempfile.TemporaryDirectory()
        jtmp = tempfile.NamedTemporaryFile(mode='w', dir=dtmp.name, delete=False)

        if isinstance(job_input, str):
            jtmp.write(job_input)
        else:
            job_input.to_json_file(jtmp)

        jtmp.close()

        args = [self._exe, jtmp.name]

        if self.debug:
            args.append('-d')

        pfea = subprocess.Popen(args, executable=self._exe, stdout=sys.stdout)

        pfea.wait()

        jrst_name = jtmp.name + '.rst'

        if not os.path.exists(jrst_name):
            return Result(False, job_input, None, errors=['Result file not found'])

        result = self.output_type.model_from_file(jrst_name)

        return Result(True, job_input, result)

class SimpleHttpAgent(_Agent):
    DEFAULT_ADDRESS = '127.0.0.1'
    DEFAULT_PORT = 8000

    def __init__(self, input_type, output_type, route, address=DEFAULT_ADDRESS, port=DEFAULT_PORT):
        super().__init__(input_type, output_type)

        self.route = route
        self.address = address
        self.port = port

    @classmethod
    def FEARunner(cls, address=DEFAULT_ADDRESS, port=DEFAULT_PORT):
        return cls(model.Model, result.Database, '/fea/run', address, port)

    @classmethod
    def MicroRunner(cls, address=DEFAULT_ADDRESS, port=DEFAULT_PORT):
        return cls(micro.Run, micro.Result, '/micro/run', address, port)

    @property
    def _url(self):
        return f'http://{self.address}:{self.port}{self.route}'

    def run_sync(self, job_input):
        data = {}
        data['model'] = ModelEncoder.object_to_dict(job_input)

        resp = requests.post(self._url, json=data)

        jresp = resp.json()

        success = jresp['success']
        errors = jresp['errors']
        result = ModelEncoder.dict_to_object(jresp['result'], self.output_type)

        return Result(
            success,
            job_input,
            result,
            errors=errors
        )
