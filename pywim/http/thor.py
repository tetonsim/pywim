from . import HttpClient, Method, Api, Route, RouteAdd, RouteParam

from .. import WimObject, WimList

class User(WimObject):
    def __init__(self):
        self.id = ''
        self.email = ''
        self.first_name = ''
        self.last_name = ''
        self.email_verified = False

class Token(WimObject):
    def __init__(self):
        self.id = ''
        self.expires = ''

class Credentials(WimObject):
    def __init__(self):
        self.success = False
        self.error = ''
        self.user = User()
        self.token = Token()

class Client(HttpClient):
    def __init__(self, address='api.fea.cloud', port=443, protocol='https'):
        super().__init__(address=address, port=port, protocol=protocol)

    def _serialize_request(self, data, request_type):
        if data and isinstance(data, (WimObject, WimList)):
            return data.to_dict()
        return data

    def _deserialize_response(self, response, response_type):
        if response_type == dict:
            return response.json()
        elif hasattr(response_type, 'from_dict'):
            return response_type.from_dict(response.json())

        return response_type(response.text)

    @property
    def auth(self):
        auth_r = Route(self, '/auth')

        def update_token(r):
            self._bearer_token = r.token.id

        def remove_token(r):
            self._bearer_token = None

        auth_r += RouteAdd(
            'token',
            apis = {
                Method.Post: Api(Credentials, dict, callback=update_token),
                Method.Put: Api(Credentials),
                Method.Delete: Api(dict, callback=remove_token)
            }
        )

        auth_r += RouteAdd(
            'whoami',
            apis = {
                Method.Get: Api(Credentials)
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
