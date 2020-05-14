from typing import Any, Tuple, Union, Optional

import enum
import requests

from pywim import WimObject, WimList

class ApiResult(WimObject):
    def __init__(self):
        self.success = False
        self.message = ''
        self.error = ''
        self.exception = ''

class User(WimObject):
    '''
    User information, such as unique Id, email, and name
    '''
    def __init__(self):
        self.id = ''
        self.email = ''
        self.first_name = ''
        self.last_name = ''
        self.email_verified = False

class Token(WimObject):
    '''
    Authentication token information
    Important! The 'id' attribute contains the token that authenticates the user
    with the server. This must be kept secret and safe.
    '''
    def __init__(self):
        self.id = ''
        self.expires = ''

class UserAuth(WimObject):
    '''
    User authentication
    '''
    def __init__(self):
        self.user = User()
        self.token = Token()

class Client:
    def __init__(self, hostname='api.smartslice.xyz', port=443, protocol='https'):
        self.hostname = hostname
        self.port = port
        self.protocol = protocol
        self._bearer_token = None

    @property
    def address(self):
        return '%s://%s:%i' % (self.protocol, self.hostname, self.port)

    def _headers(self):
        hdrs = {}
        if self._bearer_token:
            hdrs['Authorization'] = 'Bearer ' + self._bearer_token
        return hdrs

    def _request(self, method : str, endpoint : str, data : Any, **kwargs) -> requests.Response:
        if isinstance(data, bytes):
            request_args = { 'data': data }
        else:
            request_args = { 'json': data }

        request_args['headers'] = self._headers()

        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint

        url = self.address + endpoint

        return requests.request(
            method.lower(),
            url,
            **request_args
        )

    def _get(self, endpoint : str, **kwargs) -> requests.Response:
        return self._request('get', endpoint, None, **kwargs)

    def _post(self, endpoint : str, data : Any = None, **kwargs) -> requests.Response:
        return self._request('post', endpoint, data, **kwargs)

    def _put(self, endpoint : str, data : Any = None, **kwargs) -> requests.Response:
        return self._request('put', endpoint, data, **kwargs)

    def _delete(self, endpoint : str, data : Any = None, **kwargs) -> requests.Response:
        return self._request('delete', endpoint, data, **kwargs)

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

    def _code_and_object(self, resp : requests.Response, T):
        return resp.status_code, T.from_dict(resp.json())

    def basic_auth_login(self, email, password) -> Tuple[int, Union[UserAuth, ApiResult]]:
        resp = self._post(
            '/auth/token',
            {
                'email': email,
                'password': password
            }
        )

        if resp.status_code >= 500:
            return resp.status_code, None

        if resp.status_code == 200:
            auth = UserAuth.from_dict(resp.json())
            self._bearer_token = auth.token.id
            return resp.status_code, auth

        return self._code_and_object(resp, ApiResult)

    def whoami(self) -> Tuple[int, Union[UserAuth, ApiResult]]:
        resp = self._get('/auth/whoami')

        if resp.status_code >= 500:
            return resp.status_code, None

        if resp.status_code == 200:
            self._code_and_object(resp, UserAuth)

        return self._code_and_object(resp, ApiResult)

    def refresh_token(self) -> Tuple[int, Union[UserAuth, ApiResult]]:
        resp = self._put('/auth/token')

        if resp.status_code >= 500:
            return resp.status_code, None

        if resp.status_code == 200:
            # The token id will be the same, so we don't need to update it
            return self._code_and_object(resp, UserAuth)

        return self._code_and_object(resp, ApiResult)

    def release_token(self) -> Tuple[int, ApiResult]:
        resp = self._delete('/auth/token')

        if resp.status_code >= 500:
            return resp.status_code, None

        self._bearer_token = None

        return self._code_and_object(resp, ApiResult)
