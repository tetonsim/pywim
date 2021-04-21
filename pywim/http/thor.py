from typing import Any, Tuple, Union, Optional, Callable, Type, TypeVar

import enum
import datetime
import requests
import time

import pywim

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

class Product(WimObject):
    '''
    A product definition in a subscription
    '''

    class UsageType(enum.Enum):
        unlimited = 0
        limited = 1

    def __init__(self, name : str = None):
        self.name = name if name else ''
        self.usage_type = Product.UsageType.limited
        self.used = 0
        self.total = 0

class Subscription(WimObject):
    class Status(enum.Enum):
        unknown = 0
        inactive = 1
        active = 2
        trial = 3

    def __init__(self):
        default_dt = datetime.datetime(1900, 1, 1)

        self.status = Subscription.Status.unknown
        self.start = default_dt
        self.end = default_dt
        self.trial_start = default_dt
        self.trial_end = default_dt
        self.products = WimList(Product)

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
        self.runtime_estimate = 0
        self.runtime_remaining = 0
        self.runtime = 0
        self.result = pywim.smartslice.result.Result()
        self.errors = WimList(JobInfo.Error)

T = TypeVar('T')
U = TypeVar('U')
W = TypeVar('W', bound=WimObject)

ResponseType = Tuple[int, Optional[Union[T, U]]]

class Client:
    def __init__(self, hostname='api.smartslice.xyz', port=443, protocol='https', cluster=None):
        self.hostname = hostname
        self.port = port
        self.protocol = protocol
        self.cluster = cluster
        self._accept_version = '20.1'
        self._bearer_token = None

    @property
    def address(self):
        return '%s://%s:%i' % (self.protocol, self.hostname, self.port)

    def _headers(self):
        '''
        Returns a dictionary of additional headers that will be added
        to every request.
        '''
        hdrs = {
            'Accept-Version': self._accept_version
        }

        if self._bearer_token:
            hdrs['Authorization'] = 'Bearer ' + self._bearer_token

        if self.cluster:
            hdrs['SmartSlice-Cluster'] = self.cluster

        return hdrs

    def _request(self, method : str, endpoint : str, data : Any, **kwargs) -> requests.Response:
        '''
        Assembles an HTTP request and submits it using the requests library.
        '''
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

    @staticmethod
    def _code_and_object(resp : requests.Response, t : Type[W]) -> Tuple[int, W]:
        return resp.status_code, t.from_dict(resp.json())

    def get_token(self) -> str:
        return self._bearer_token

    def set_token(self, token_id : str):
        '''
        Set the auth token explicitly. This is useful if the token was stored
        and retrieved locally.
        '''
        self._bearer_token = token_id

    def info(self) -> Tuple[int, Optional[dict]]:
        resp = self._get('/')

        if resp.status_code == 200:
            return resp.status_code, resp.json()

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        return resp.status_code, None

    def basic_auth_login(self, email, password) -> 'ResponseType[UserAuth, ApiResult]':
        resp = self._post(
            '/auth/token',
            {
                'email': email,
                'password': password
            }
        )

        if resp.status_code in (429, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        if resp.status_code == 200:
            auth = UserAuth.from_dict(resp.json())
            self._bearer_token = auth.token.id
            return resp.status_code, auth

        return Client._code_and_object(resp, ApiResult)

    def whoami(self) -> 'ResponseType[UserAuth, ApiResult]':
        resp = self._get('/auth/whoami')

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        if resp.status_code == 200:
            return Client._code_and_object(resp, UserAuth)

        return Client._code_and_object(resp, ApiResult)

    def refresh_token(self) -> 'ResponseType[UserAuth, ApiResult]':
        resp = self._put('/auth/token')

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        if resp.status_code == 200:
            # The token id will be the same, so we don't need to update it
            return Client._code_and_object(resp, UserAuth)

        return Client._code_and_object(resp, ApiResult)

    def release_token(self) -> Tuple[int, Optional[ApiResult]]:
        resp = self._delete('/auth/token')

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        self._bearer_token = None

        return Client._code_and_object(resp, ApiResult)

    def new_smartslice_job(self, tmf : bytes) -> 'ResponseType[JobInfo, ApiResult]':
        '''
        Submits the provided 3MF as a new job and returns the new JobInfo object.
        '''
        resp = self._post('/smartslice', tmf)

        if resp.status_code in (401, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        return Client._code_and_object(resp, JobInfo)

    def smartslice_job(self, job_id : str, include_results : bool = False) -> 'ResponseType[JobInfo, ApiResult]':
        '''
        Retrieves a JobInfo object from an existing job id. Will return a 404
        if the user doesn't have access to the specified job.
        '''
        if include_results:
            resp = self._get('/smartslice/result/%s' % job_id)
        else:
            resp = self._get('/smartslice/%s' % job_id)

        if resp.status_code in (401, 404, 429, 500):
            return resp.status_code, None

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        return Client._code_and_object(resp, JobInfo)

    def smartslice_job_abort(self, job_id : str) -> Tuple[int, Optional[JobInfo]]:
        '''
        Requests the job with the given id should be aborted. This will return
        the updated JobInfo object to reflect the new status after the server
        processes the abort request.
        '''
        resp = self._delete('/smartslice/%s' % job_id)

        if resp.status_code == 400:
            return Client._code_and_object(resp, ApiResult)

        if resp.status_code == 200:
            return Client._code_and_object(resp, JobInfo)

        return resp.status_code, None

    def smartslice_job_wait(
        self,
        job_id : str,
        timeout : int = 600,
        callback : Callable[[JobInfo], bool] = None
    ) -> 'ResponseType[JobInfo, ApiResult]':
        '''
        This is a blocking function that will periodically poll the job status until
        it completes. Additionally, a timeout parameter can be given to specify the maximum
        amount of time, in seconds, to poll for. A callback function can be provided
        that will be called periodically with the JobInfo object so the caller can take
        actions as the job progresses. The callback must return a bool specifying if the
        job should be aborted (True) or not (False).
        '''

        start_period = 1
        max_poll_period = 30
        poll_multiplier = 1.5

        fperiod = lambda previous_period: min(max_poll_period, previous_period * poll_multiplier)

        period = start_period
        start_poll = time.time()

        while True:
            time.sleep(period)
            period = fperiod(period)

            status_code, job = self.smartslice_job(job_id, include_results=True)

            if status_code == 429:
                # We hit a rate limit, so check again after the poll period
                continue

            if status_code != 200:
                return status_code, job

            assert isinstance(job, JobInfo)

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

    def smartslice_subscription(self) -> 'ResponseType[Subscription, ApiResult]':
        '''
        Retrieve the user's subscription. If the user does not have
        a subscription a Subscription object with no Products will
        be returned.
        '''
        resp = self._get('/smartslice/subscription')

        if resp.status_code in (401, 429, 500):
            return resp.status_code, None

        return Client._code_and_object(resp, Subscription)
