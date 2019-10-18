import enum
import requests

from collections import namedtuple

from typing import TypeVar, Generic, List

from . import Meta, WimObject, WimList, WimException
from . import chop, micro
from . import fea as _fea # need to redefine so we can use "fea" as a property in solver client

T = TypeVar('T', WimObject, int)

class Methods(enum.Enum):
    Get = 1
    Post = 2
    Put = 3
    Delete = 4

class Api:
    def __init__(self, response_type, request_type=None, callback=None):
        self.response_type = response_type
        self.request_type = request_type
        self.callback = callback

class Route:
    def __init__(self, client, endpoint, apis=None):
        self.client = client
        self.endpoint = endpoint
        self.apis = apis if apis else {}

    def _get_api(self, method):
        api = self.apis.get(method)
        if api is None:
            raise WimException(
                '%s method is not available on %s' % (method.name, self.client._url(self.endpoint))
            )
        return api

    def get(self):
        api = self._get_api(Methods.Get)
        return self.client._get(
            self.endpoint,
            api.response_type
        )

    def post(self, data=None):
        api = self._get_api(Methods.Post)
        return self.client._post(
            self.endpoint,
            api.response_type,
            data
        )

    def put(self, data=None):
        api = self._get_api(Methods.Put)
        return self.client._put(
            self.endpoint,
            api.response_type,
            data
        )

    def delete(self):
        api = self._get_api(Methods.Delete)
        return self.client._delete(
            self.endpoint,
            api.response_type
        )

class HttpClient:
    DEFAULT_ADDRESS = '127.0.0.1'
    DEFAULT_PORT = 8000

    def __init__(self, address=DEFAULT_ADDRESS, port=DEFAULT_PORT, protocol='https'):
        self.address = address
        self.port = port
        self.protocol = protocol
        self._bearer_token = None

    def _url(self, endpoint):
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        return f'{self.protocol}://{self.address}:{self.port}{endpoint}'

    def _headers(self):
        hdrs = {}
        if self._bearer_token:
            hdrs['Authorization'] = 'Bearer ' + self._bearer_token

    def _get(self, endpoint, response_type, *args, **kwargs):
        raise NotImplementedError()

    def _post(self, endpoint, response_type, data, *args, **kwargs):
        raise NotImplementedError()

    def _put(self, endpoint, response_type, data, *args, **kwargs):
        raise NotImplementedError()

    def _delete(self, endpoint, response_type, *args, **kwargs):
        raise NotImplementedError()

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
        return hdrs

    def _get(self, endpoint, response_type : T) -> WimSolverResponse[T]:
        http_resp = requests.get(
            self._url(endpoint),
            headers=self._headers()
        )
        
        if response_type == ServerInfo:
            # This is kind of hacky. The / endpoint doesn't
            # return the response JSON in the usual format, so we
            # handle it differently
            return ServerInfo.from_dict(http_resp.json())

        return WimSolverResponse.from_dict(http_resp, response_type)

    def _post(self, endpoint, response_type : T, data) -> WimSolverResponse[T]:
        if isinstance(data, (WimObject, WimList)):
            data = self._input_dict(data)
        http_resp = requests.post(
            self._url(endpoint),
            json=data,
            headers=self._headers()
        )
        return WimSolverResponse.from_dict(http_resp, response_type)

    @property
    def info(self):
        return Route(
            self,
            '/',
            apis = {
                Methods.Get: Api(ServerInfo)
            }
        )

    @property
    def fea(self):
        fea_r = Route(self, '/fea')
        
        fea_r.stats = Route(
            self,
            '/fea/stats',
            apis = {
                Methods.Post: Api(int, _fea.model.Model)
            }
        )

        fea_r.solve = Route(
            self,
            '/fea/run',
            apis = {
                Methods.Post: Api(_fea.result.Database, _fea.model.Model)
            }
        )

        return fea_r

    @property
    def micro(self):
        micro_r = Route(self, '/micro')
        
        micro_r.solve = Route(
            self,
            '/micro/run',
            apis = {
                Methods.Post: Api(micro.Result, micro.Run)
            }
        )

        return micro_r

    @property
    def chop(self):
        chop_r = Route(self, '/chop')
        
        chop_r.slice = Route(
            self,
            '/chop/slice',
            apis = {
                Methods.Post: Api(int, chop.job.Job)
            }
        )

        chop_r.voxel = Route(
            self,
            '/chop/voxel',
            apis = {
                Methods.Post: Api(_fea.model.Mode, chop.job.Job)
            }
        )

        return chop_r

class HttpThorClient(HttpClient):
    def __init__(self, address=HttpClient.DEFAULT_ADDRESS, port=HttpClient.DEFAULT_PORT, protocol='https'):
        super().__init__(address=address, port=port, protocol=protocol)

    def _get(self, endpoint, response_type : T) -> T:
        http_resp = requests.get(
            self._url(endpoint),
            headers=self._headers()
        )

        return response_type.from_dict(http_resp.json())

    def _post(self, endpoint, response_type : T, data) -> T:
        if isinstance(data, (WimObject, WimList)):
            data = data.to_dict()

        http_resp = requests.post(
            self._url(endpoint),
            json=data,
            headers=self._headers()
        )

        return response_type.from_dict(http_resp)

    @property
    def auth(self):
        pass


