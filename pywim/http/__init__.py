import enum
import requests
import urllib.parse

from .. import WimException

class WimHttpException(WimException):
    pass

class ClientException(WimHttpException):
    pass

class ServerException(WimHttpException):
    def __init__(self, response, message):
        super().__init__(message)
        self.response = response

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
            raise ClientException(
                '%s method is not available on %s' % (method.name, self.client._url(route.endpoint))
            )
        return api

    def _call_client(self, method, data=None, **kwargs):
        route = self._get_route(**kwargs)
        api = self._get_api(route, method)

        endpoint = route.endpoint if isinstance(route, Route) else self.endpoint + route.endpoint

        resp_data = self.client(api, method, endpoint, data, **kwargs)

        if api.callback:
            api.callback(resp_data)

        return resp_data

    def get(self, **kwargs):
        return self._call_client(Method.Get, **kwargs)

    def post(self, data=None, **kwargs):
        return self._call_client(Method.Post, data, **kwargs)

    def put(self, data=None, **kwargs):
        return self._call_client(Method.Put, data, **kwargs)

    def delete(self, **kwargs):
        return self._call_client(Method.Delete, **kwargs)

class HttpClient:
    DEFAULT_HOSTNAME = '127.0.0.1'
    DEFAULT_PORT = 8000

    def __init__(self, hostname=DEFAULT_HOSTNAME, port=DEFAULT_PORT, protocol='https'):
        self.hostname = hostname
        self.port = port
        self.protocol = protocol
        self._bearer_token = None

    @property
    def address(self):
        return '%s://%s:%i' % (self.protocol, self.hostname, self.port)

    def _url(self, endpoint, **kwargs):
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint

        url = self.address + endpoint

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

    def _serialize_request(self, data, request_type):
        return data

    def _deserialize_response(self, response, response_type):
        return response.json()

    def __call__(self, api, method, endpoint, data, **kwargs):
        data = self._serialize_request(data, api.request_type)

        if isinstance(data, bytes):
            request_args = { 'data': data }
        else:
            request_args = { 'json': data }

        request_args['headers'] = self._headers()

        http_resp = requests.request(
            method.name.lower(),
            self._url(endpoint, **kwargs),
            **request_args
        )

        if int(http_resp.status_code / 100) == 4:
            self._handle_4XX_status_code(http_resp, method, endpoint)
        elif int(http_resp.status_code / 100) == 5:
            self._handle_5XX_status_code(http_resp, method, endpoint)

        return self._deserialize_response(http_resp, api.response_type)
        #raise ServerException(http_resp, 'HTTP client cannot handle %i status code' % http_resp.status_code)

    def _handle_4XX_status_code(self, response, method, endpoint):
        call_name = '%s %s' % (method.name.upper(), endpoint)
        if response.status_code == 401:
            raise ServerException(
                response,
                'Unauthorized HTTP request on %s' % call_name
            )
        elif response.status_code == 404:
            raise ServerException(
                response,
                'Not found on %s' % call_name
            )
        raise ServerException(
            response,
            'Unknown HTTP error %i on %s' % (response.status_code, call_name)
        )

    def _handle_5XX_status_code(self, response, method, endpoint):
        call_name = '%s %s' % (method.name.upper(), endpoint)
        raise ServerException(
            response,
            'HTTP server error %i on %s' % (response.status_code, call_name)
        )

from . import smartslice, wim
