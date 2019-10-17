import os
import sys
import tempfile
import subprocess
import requests

from typing import TypeVar, Generic, List

from . import Meta, WimObject, WimList
from . import chop, fea, micro

T = TypeVar('T', WimObject, int)

class Response(Generic[T]):
    def __init__(self, success : bool = False, result : T = None, errors : List[str] = None):
        self.success = success
        self.result = result
        self.errors = errors
        self.log = None

    @classmethod
    def from_dict(cls, dresp : dict, result_type : T = None):
        r = cls()
        r.success = dresp.get('success', False)
        r.errors = dresp.get('errors', [])
        r.log = dresp.get('log')
        
        dresult = dresp.get('result', {})
        
        if result_type:
            if WimObject in result_type.__bases__:
                r.result = result_type.from_dict(dresult)
            else:
                r.result = result_type(dresult)
        else:
            r.result = dresult

        return r

class ServerInfo(WimObject):
    def __init__(self):
        self.load = dict()
        self.meta = Meta()

class HttpClient:
    DEFAULT_ADDRESS = '127.0.0.1'
    DEFAULT_PORT = 8000

    def __init__(self, address=DEFAULT_ADDRESS, port=DEFAULT_PORT, protocol='https'):
        self.address = address
        self.port = port
        self.protocol = protocol

    def _url(self, route):
        if not route.startswith('/'):
            route = '/' + route
        return f'{self.protocol}://{self.address}:{self.port}{route}'

    def _get(self, route, result_type : T = None) -> Response[T]:
        http_resp = requests.get(self._url(route))
        return Response.from_dict(http_resp.json(), result_type)

    def _post(self, route, data, result_type : T = None) -> Response[T]:
        if isinstance(data, (WimObject, WimList)):
            data = data.to_dict()
        http_resp = requests.post(self._url(route), json=data)
        return Response.from_dict(http_resp.json(), result_type)

class HttpSolverClient(HttpClient):
    def __init__(self, address=HttpClient.DEFAULT_ADDRESS, port=HttpClient.DEFAULT_PORT, protocol='http'):
        super().__init__(address=address, port=port, protocol=protocol)

        self._process = None

    def __del__(self):
        if self._process:
            pass # TODO stop it

    @classmethod
    def CreateAndStart(cls, address='127.0.0.1', port=HttpClient.DEFAULT_PORT, exe_name='wim-httpd', exe_path=None):
        client = HttpClient(address, port)

        # TODO Attempt to start

        return client()

    def _input_dict(self, mdl : WimObject):
        return {
            'model': mdl.to_dict()
        }

    def info(self) -> Response:
        return self._get('/', ServerInfo)

    def fea_stats(self, fea_model : fea.model.Model) -> Response[int]:
        return self._post(
            '/fea/stats',
            self._input_dict(fea_model),
            int
        )

    def fea_solve(self, fea_model : fea.model.Model) -> Response[fea.result.Database]:
        return self._post(
            '/fea/run',
            self._input_dict(fea_model),
            fea.result.Database
        )

    def micro_run(self, micro_model: micro.Run) -> Response[micro.Result]:
        return self._post(
            '/micro/run',
            self._input_dict(micro_model),
            micro.Result
        )

    def chop_slice(self, chop_job: chop.job.Job) -> Response[int]:
        return self._post(
            '/chop/slice',
            self._input_dict(chop_job),
            int
        )

    def chop_voxel(self, chop_job: chop.job.Job) -> Response[fea.model.Model]:
        return self._post(
            '/chop/voxel',
            self._input_dict(chop_job),
            fea.model.Model
        )
