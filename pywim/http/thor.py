from typing import Any, Tuple, Union, Optional, Callable

import enum
import datetime
import requests
import time

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
    User authentication response
    '''
    def __init__(self):
        self.user = User()
        self.token = Token()

class JobInfo(WimObject):
    class Type(enum.Enum):
        validation = 101
        optimizaton = 102

    class Status(enum.Enum):
        idle = 101          # Created, but not submitted to a queue
        queued = 102        # Job in queue, but not picked up by an engine yet
        running = 201       # Job is being solved
        finished = 301      # Finished and results are available
        aborted = 401       # Aborted by the user. A run can be aborted before or after it enters the running state
        failed = 402        # The job started, but failed in a graceful fashion. A helpful error message should be available.
        crashed = 403       # The job started, but the process crashed. Helpful error messages are probably not available (e.g. seg fault)

    class Error(WimObject):
        def __init__(self):
            self.message = ''

    def __init__(self):
        default_dt = datetime.datetime(1900, 1, 1)

        self.id = ''
        #self.type = JobInfo.Type.validation
        self.status = JobInfo.Status.idle
        self.progress = 0
        self.queued = default_dt
        self.started = default_dt
        self.finished = default_dt
        self.start_estimate = default_dt
        self.runtime_estimate = ''
        self.runtime = 0
        self.result = {}
        self.errors = WimList(JobInfo.Error)

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

    def get_token(self) -> str:
        return self._bearer_token

    def set_token(self, token_id : str):
        '''
        Set the auth token explicitly. This is useful if the token was stored
        and retrieved locally
        '''
        self._bearer_token = token_id

    def info(self) -> Tuple[int, dict]:
        resp = self._get('/')

        if resp.status_code == 200:
            return resp.status_code, resp.json()

        return resp.status_code, None

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

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 200:
            return self._code_and_object(resp, UserAuth)

        return self._code_and_object(resp, ApiResult)

    def refresh_token(self) -> Tuple[int, Union[UserAuth, ApiResult]]:
        resp = self._put('/auth/token')

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 200:
            # The token id will be the same, so we don't need to update it
            return self._code_and_object(resp, UserAuth)

        return self._code_and_object(resp, ApiResult)

    def release_token(self) -> Tuple[int, ApiResult]:
        resp = self._delete('/auth/token')

        if resp.status_code in (401, 500):
            return resp.status_code, None

        self._bearer_token = None

        return self._code_and_object(resp, ApiResult)

    def new_smartslice_job(self, tmf : bytes) -> Tuple[int, Union[JobInfo, ApiResult]]:
        resp = self._post('/smartslice', tmf)

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return self._code_and_object(resp, ApiResult)

        return self._code_and_object(resp, JobInfo)

    def smartslice_job(self, job_id : str, include_results : bool = False) -> Tuple[int, Union[JobInfo, ApiResult]]:
        if include_results:
            resp = self._get('/smartslice/result/%s' % job_id)
        else:
            resp = self._get('/smartslice/%s' % job_id)

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return self._code_and_object(resp, ApiResult)

        return self._code_and_object(resp, JobInfo)

    def smartslice_job_abort(self, job_id : str) -> Tuple[int, Optional[JobInfo]]:
        resp = self._delete('/smartslice/%s' % job_id)

        if resp.status_code == 200:
            return self._code_and_object(resp, JobInfo)

        return resp.status_code, None

    def smartslice_job_wait(
        self,
        job_id : str,
        timeout : int = 600,
        callback : Callable[[JobInfo], bool] = None
    ) -> Tuple[int, Union[JobInfo, ApiResult]]:
        start_period = 1
        max_poll_period = 30
        poll_multiplier = 1.25

        fperiod = lambda previous_period: min(max_poll_period, previous_period * poll_multiplier)

        period = start_period
        start_poll = time.time()

        while True:
            time.sleep(period)
            period = fperiod(period)

            status_code, job = self.smartslice_job(job_id, include_results=True)

            if status_code != 200:
                return status_code, job

            if job.status in (
                JobInfo.Status.finished,
                JobInfo.Status.failed,
                JobInfo.Status.aborted,
                JobInfo.Status.crashed
            ):
                break

            if timeout is not None and (time.time() - start_poll) > timeout:
                break

            if callback:
                abort = callback(job)
                if abort:
                    return self.smartslice_job_abort(job.id)

        return status_code, job
