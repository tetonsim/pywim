from . import HttpClient, Method, Api, Route, RouteAdd, RouteParam

import requests
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
            r.errors.append(f'Server returned error code {http_response.status_code}')
        
        return r

class ServerInfo(WimObject):
    def __init__(self):
        self.load = dict()
        self.meta = Meta()

class Client(HttpClient):
    def __init__(self, hostname=HttpClient.DEFAULT_HOSTNAME, port=HttpClient.DEFAULT_PORT, protocol='http'):
        super().__init__(hostname=hostname, port=port, protocol=protocol)

        self._process = None

    def __del__(self):
        if self._process:
            pass # TODO stop it

    @classmethod
    def CreateAndStart(cls, hostname='127.0.0.1', port=HttpClient.DEFAULT_PORT, exe_name='wim-httpd', exe_path=None):
        client = HttpClient(hostname, port)

        # TODO Attempt to start

        return client()

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
                Method.Post: Api(int, chop.job.Job)
            }
        )

        chop_r += RouteAdd(
            'voxel',
            apis = {
                Method.Post: Api(_fea.model.Model, chop.job.Job)
            }
        )

        return chop_r