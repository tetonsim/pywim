from . import HttpClient, Method, Api, Route, RouteAdd, RouteParam

import os
import requests
import subprocess
from typing import TypeVar, Generic, List

from .. import WimObject, WimList, Meta
from .. import fea as _fea # need to redefine so we can use "fea" as a property in solver client
from .. import chop, micro

T = TypeVar('T', WimObject, int)

class WimSolverResponse(Generic[T]):
    def __init__(self, success : bool = False, result : T = None, errors : List[str] = None):
        self.success = success
        self.result = result
        self.errors = errors
        self.log = None

    @classmethod
    def from_dict(cls, http_response : requests.Response, response_type : T = None):
        dresp = http_response.json()

        r = cls()
        r.success = dresp.get('success', False)
        r.errors = dresp.get('errors', [])
        r.log = dresp.get('log')

        dresult = dresp.get('result', {})

        if response_type:
            if WimObject in response_type.__bases__:
                r.result = response_type.from_dict(dresult)
            else:
                r.result = response_type(dresult)
        else:
            r.result = dresult

        if http_response.status_code >= 400:
            r.success = False
            r.errors.append('Server returned error code %i' % http_response.status_code)

        return r

class ServerInfo(WimObject):
    class Options(WimObject):
        def __init__(self):
            self.port = 8000
            self.threads = 1
            self.max_request_mb = 0
            self.max_response_mb = 0

    def __init__(self):
        self.load = dict()
        self.meta = Meta()
        self.options = ServerInfo.Options()

class Client(HttpClient):
    def __init__(self, hostname=HttpClient.DEFAULT_HOSTNAME, port=HttpClient.DEFAULT_PORT, protocol='http'):
        super().__init__(hostname=hostname, port=port, protocol=protocol)

        self._process = None
        self._process_starter = None

    def __del__(self):
        self.close()

    def close(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def health_check(self):
        '''
        If the solver process was started, this will check if it's still running,
        and if not, restart the process.
        '''
        if self._process:
            if self._process.poll() is not None:
                self._start_solver()

    @classmethod
    def CreateAndStart(cls, port=HttpClient.DEFAULT_PORT, exe_name='wim-httpd', exe_path=None,
        debug=False, threads=1):

        hostname = '127.0.0.1'

        client = Client(hostname, port)

        exe = exe_name if not exe_path else os.path.join(exe_path, exe_name)

        args = [
            exe,
            '-p', str(port),
            '-t', str(threads)
        ]

        if debug:
            args.append('-d')

        client._process_starter = lambda: subprocess.Popen(args=args, executable=exe)
        client._start_solver()

        return client

    def _start_solver(self):
        self._process = self._process_starter()

        poll = self._process.poll()

        if poll:
            raise Exception('Solver process immediately exited with return code %i' % self._process.returncode)

    def _handle_4XX_status_code(self, response, method, endpoint):
        # Override the default 4XX status code handler so we don't
        # raise an exception.
        # The wim solver server passes all the same stuff pack on
        # a 4XX error so let's process it as usual.
        pass

    def _serialize_request(self, data, request_type):
        if data and isinstance(data, (WimObject, WimList)):
            return {
                'model': data.to_dict()
            }
        return data

    def _deserialize_response(self, response, response_type):
        if response_type == ServerInfo:
            # This is kind of hacky. The / endpoint doesn't
            # return the response JSON in the usual format, so we
            # handle it differently
            return ServerInfo.from_dict(response.json())

        return WimSolverResponse.from_dict(response, response_type)

    @property
    def info(self):
        return Route(
            self,
            '/',
            apis = {
                Method.Get: Api(ServerInfo)
            }
        )

    @property
    def fea(self):
        fea_r = Route(self, '/fea')

        fea_r += RouteAdd(
            'stats',
            apis = {
                Method.Post: Api(int, _fea.model.Model)
            }
        )

        fea_r += RouteAdd(
            'run',
            apis = {
                Method.Post: Api(_fea.result.Database, _fea.model.Model)
            },
            alias = 'solve'
        )

        return fea_r

    @property
    def micro(self):
        micro_r = Route(self, '/micro')

        micro_r += RouteAdd(
            'run',
            apis = {
                Method.Post: Api(micro.Result, micro.Run)
            },
            alias = 'solve'
        )

        return micro_r

    @property
    def chop(self):
        chop_r = Route(self, '/chop')

        chop_r += RouteAdd(
            'slice',
            apis = {
                Method.Post: Api(int, chop.model.Model)
            }
        )

        chop_r += RouteAdd(
            'voxel',
            apis = {
                Method.Post: Api(_fea.model.Model, chop.model.Model)
            }
        )

        return chop_r