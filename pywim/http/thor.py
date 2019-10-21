import enum

from . import HttpClient, Method, Api, Route, RouteAdd, RouteParam

from .. import WimObject, WimList
from .. import smartslice

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

class UserAuth(WimObject):
    def __init__(self):
        self.success = False
        self.error = ''
        self.user = User()
        self.token = Token()

class UploadStatus(WimObject):
    def __init__(self):
        self.name = None
        self.success = False
        self.error = None
        self.md5 = None

class NewSmartSliceJob(WimObject):
    def __init__(self, name : str, job_type : smartslice.job.JobType):
        self.name = name
        self.type = job_type

class SmartSliceJobStatus(enum.Enum):
    new = 1
    submitted = 2
    running = 3
    failed = 4
    finished = 5

class SmartSliceJob(WimObject):
    def __init__(self):
        self.id = None
        self.name = None
        self.type = smartslice.job.JobType.validation
        self.status = SmartSliceJobStatus()
        self.size = 0
        self.deleted = False

class JobSubmission(WimObject):
    def __init__(self):
        self.job = SmartSliceJob()
        self.success = False
        self.error = None

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
                Method.Post: Api(UserAuth, dict, callback=update_token),
                Method.Put: Api(UserAuth),
                Method.Delete: Api(dict, callback=remove_token)
            }
        )

        auth_r += RouteAdd(
            'whoami',
            apis = {
                Method.Get: Api(UserAuth)
            }
        )

        return auth_r

    @property
    def smart_slice(self):
        ss_r = Route(
            self,
            '/is',
            apis = {
                Method.Get: Api(WimList(SmartSliceJob)),
                Method.Post: Api(SmartSliceJob, NewSmartSliceJob)
            }
        )

        ss_r += RouteParam(
            'id',
            apis = {
                Method.Get: Api(SmartSliceJob),
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
                Method.Post: Api(UploadStatus, bytes),
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
                Method.Post: Api(JobSubmission)
            }
        )

        return ss_r
