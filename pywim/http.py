import enum
import requests
import urllib.parse

from typing import TypeVar, Generic, List

from . import Meta, WimObject, WimList, WimException
from . import chop, micro
from . import fea as _fea # need to redefine so we can use "fea" as a property in solver client

T = TypeVar('T', WimObject, int)

class Method(enum.Enum):
    Get = 1
    Post = 2
    Put = 3
    Delete = 4

class Api:
    def __init__(self, response_type, request_type=None, callback=None):
        self.response_type = response_type
        self.request_type = request_type
        self.callback = callback

class RouteAdd:
    def __init__(self, endpoint, apis=None, alias=None):
        self.endpoint = endpoint
        self.apis = apis
        self.alias = alias

class RouteParam:
    def __init__(self, params, apis=None):
        self.params = params if isinstance(params, (tuple, list)) else (params, )
        self.apis = apis

    @property
    def endpoint(self):
        ep = ''
        for p in self.params:
            ep += ('/{%s}' % p)
        return ep

class Route:
    def __init__(self, client, endpoint, apis=None):
        self.client = client
        self.endpoint = endpoint
        self.apis = apis if apis else {}
        self._sub_routes = []
        self._params = []

    def __iadd__(self, other):
        if isinstance(other, RouteAdd):
            slash_index = other.endpoint.find('/')
            name = other.endpoint[:slash_index] if slash_index > 0 else other.endpoint
            sub_route = Route(self.client, self.endpoint.rstrip('/') + '/' + name, other.apis)
            self._sub_routes.append(sub_route)
            attr_name = other.alias if other.alias else name
            self.__dict__[attr_name] = sub_route
        elif isinstance(other, RouteParam):
            self._params.append(other)

        return self

    def _get_route(self, **kwargs):
        # Look to see if any of the RouteParam variations are satisfied from kwargs
        r = self
        max_args = 0
        for p in self._params:
            all_args_provided = all(n in kwargs.keys() for n in p.params)
            if all_args_provided and len(p.params) > max_args:
                max_args = len(p.params)
                r = p
        return r

    def _get_api(self, route, method):
        api = route.apis.get(method)
        if api is None:
            raise WimException(
                '%s method is not available on %s' % (method.name, self.client._url(route.endpoint))
            )
        return api

    def _call_client(self, method, request_method, data=None, **kwargs):
        route = self._get_route(**kwargs)
        api = self._get_api(route, method)

        endpoint = route.endpoint if isinstance(route, Route) else self.endpoint + route.endpoint

        http_resp = self.client(
            request_method,
            endpoint,
            api.response_type,
            data,
            **kwargs
        )

        if api.callback:
            api.callback(http_resp)

        return http_resp

    def get(self, **kwargs):
        return self._call_client(Method.Get, requests.get, **kwargs)

    def post(self, data=None, **kwargs):
        return self._call_client(Method.Post, requests.post, data, **kwargs)

    def put(self, data=None, **kwargs):
        return self._call_client(Method.Put, requests.put, data, **kwargs)

    def delete(self, **kwargs):
        return self._call_client(Method.Delete, requests.delete, **kwargs)

class HttpClient:
    DEFAULT_ADDRESS = '127.0.0.1'
    DEFAULT_PORT = 8000

    def __init__(self, address=DEFAULT_ADDRESS, port=DEFAULT_PORT, protocol='https'):
        self.address = address
        self.port = port
        self.protocol = protocol
        self._bearer_token = None

    def _url(self, endpoint, **kwargs):
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint

        url = f'{self.protocol}://{self.address}:{self.port}{endpoint}'

        # If there are keyword arguments search for a tag with the arg
        # name, {name}, in the url. If it exists, replace it with the value
        # Otherwise, add the argument name and value to the query string
        if len(kwargs) > 0:
            query_params = {}
            for n, v in kwargs.items():
                nt = '{%s}' % n
                if nt in url:
                    url = url.replace(
                        nt, urllib.parse.quote(str(v))
                    )
                else:
                    query_params[n] = v
            if len(query_params) > 0:
                url += '?' + urllib.parse.urlencode(query_params)

        return url

    def _headers(self):
        hdrs = {}
        if self._bearer_token:
            hdrs['Authorization'] = 'Bearer ' + self._bearer_token
        return hdrs

    def __call__(self, request_method, endpoint, response_type, data, **kwargs):
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

class SolverClient(HttpClient):
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

    def __call__(self, request_method, endpoint, response_type : T, data=None, **kwargs) -> T:
        if data and isinstance(data, (WimObject, WimList)):
            data = self._input_dict(data)

        http_resp = request_method(
            self._url(endpoint, **kwargs),
            headers=self._headers(),
            json=data
        )
        
        if response_type == ServerInfo:
            # This is kind of hacky. The / endpoint doesn't
            # return the response JSON in the usual format, so we
            # handle it differently
            return ServerInfo.from_dict(http_resp.json())

        return WimSolverResponse.from_dict(http_resp, response_type)

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
                Method.Post: Api(_fea.model.Mode, chop.job.Job)
            }
        )

        return chop_r

class ThorClient(HttpClient):
    def __init__(self, address='api.fea.cloud', port=443, protocol='https'):
        super().__init__(address=address, port=port, protocol=protocol)

    @staticmethod
    def _cast_response(http_resp, response_type):
        if response_type == dict:
            return http_resp.json()
        elif hasattr(response_type, 'from_dict'):
            return response_type.from_dict(http_resp)

        return response_type(http_resp.text)

    def __call__(self, request_method, endpoint, response_type : T, data=None, **kwargs) -> T:
        if data and isinstance(data, (WimObject, WimList)):
            data = data.to_dict()

        print(self._url(endpoint, **kwargs))

        http_resp = request_method(
            self._url(endpoint, **kwargs),
            headers=self._headers(),
            json=data
        )

        return ThorClient._cast_response(http_resp, response_type)

    @property
    def auth(self):
        auth_r = Route(self, '/auth')

        auth_r += RouteAdd(
            'register'
        )

        auth_r.register += RouteAdd(
            'setup',
            apis = {
                Method.Post: Api(bool, dict)
            }
        )

        def update_token(r):
            self._bearer_token = r['token']['id']

        def remove_token(r):
            self._bearer_token = None

        auth_r += RouteAdd(
            'token',
            apis = {
                Method.Post: Api(dict, dict, callback=update_token),
                Method.Put: Api(dict),
                Method.Delete: Api(dict, callback=remove_token)
            }
        )

        auth_r += RouteAdd(
            'whoami',
            apis = {
                Method.Get: Api(dict)
            }
        )

        return auth_r

    @property
    def smart_slice(self):
        ss_r = Route(
            self,
            '/is',
            apis = {
                Method.Get: Api(WimList(dict)),
                Method.Post: Api(dict, dict)
            }
        )

        ss_r += RouteParam(
            'id',
            apis = {
                Method.Get: Api(dict),
                Method.Delete: Api(bool)
            }
        )

        ss_r += RouteAdd(
            'file'
        )

        ss_r.file += RouteParam(
            'id',
            apis = {
                Method.Get: Api(bytes),
                Method.Delete: Api(bool)
            }
        )

        ss_r += RouteAdd(
            'exec',
            alias = 'execute'
        )

        ss_r.execute += RouteParam(
            'id',
            apis = {
                Method.Post: Api(dict)
            }
        )

        return ss_r
