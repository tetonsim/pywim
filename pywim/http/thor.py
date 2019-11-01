import enum

from . import HttpClient, Method, Api, Route, RouteAdd, RouteParam

from .. import WimObject, WimList, smartslice

class LoginRequest(WimObject):
    '''
    Provides user credentials for a login request to Thor API
    '''
    def __init__(self, email, password):
        self.email = email
        self.password = password

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
        self.success = False
        self.error = ''
        self.user = User()
        self.token = Token()

class NewTask(WimObject):
    '''
    Information required to create a new Smart Slice task in the Thor database.
    '''
    def __init__(self, name : str):
        self.name = name

class TaskStatus(enum.Enum):
    new = 1
    submitted = 2
    running = 3
    failed = 4
    finished = 5

class Task(WimObject):
    '''
    Details about a Smart Slice task stored in the Thor database. Instances of this
    class are returned by the Thor server.
    '''
    def __init__(self):
        self.id = None
        self.name = None
        #self.type = smartslice.job.JobType.validation
        self.status = TaskStatus.new
        self.size = 0
        self.deleted = False

class TaskSubmission(WimObject):
    '''
    The status of a Smart Slice task submission, returned by the Thor server.
    '''
    def __init__(self):
        self.task = Task()
        self.success = False
        self.error = None

class AssetUrl(WimObject):
    '''
    Information about a pre-signed URL used for downloading (GET) or
    uploading (PUT) a file/asset.

    :param str url: Pre-signed URL
    '''
    def __init__(self):
        self.url = ''
        self.method = ''
        self.file_name = ''
        self.exists = False

class Client(HttpClient):
    def __init__(self, hostname='api.fea.cloud', port=443, protocol='https'):
        super().__init__(hostname=hostname, port=port, protocol=protocol)

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
        '''
        Provides all auth routes
        '''
        auth_r = Route(self, '/auth')

        def update_token(r):
            self._bearer_token = r.token.id

        def remove_token(r):
            self._bearer_token = None

        auth_r += RouteAdd(
            'token',
            apis = {
                Method.Post: Api(UserAuth, LoginRequest, callback=update_token),
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
                Method.Get: Api(WimList(Task)),
                Method.Post: Api(Task, NewTask)
            }
        )

        ss_r += RouteParam(
            'id',
            apis = {
                Method.Get: Api(Task),
                Method.Delete: Api(bool)
            }
        )

        ss_r += RouteAdd(
            'file'
        )

        ss_r.file += RouteParam(
            'id',
            apis = {
                Method.Get: Api(AssetUrl),
                Method.Post: Api(AssetUrl),
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
                Method.Post: Api(TaskSubmission)
            }
        )

        return ss_r

class SimpleTask(WimObject):
    def __init__(self):
        self.id = ''
        self.started = ''
        self.finished = ''
        self.runtime = 0
        self.status = TaskStatus.new
        self.result = smartslice.result.Result()

class Client2019POC(HttpClient):
    def __init__(self, hostname='api-19.fea.cloud', port=443, protocol='https'):
        super().__init__(hostname=hostname, port=port, protocol=protocol)

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
    def submit(self):
        return Route(
            self,
            '/submit',
            apis = {
                Method.Post: Api(SimpleTask, bytes)
            }
        )

    @property
    def status(self):
        status_r = Route(
            self,
            '/task'
        )

        status_r += RouteParam(
            'id',
            apis = {
                Method.Get: Api(SimpleTask)
            }
        )

        return status_r

    @property
    def result(self):
        result_r = Route(
            self,
            '/result'
        )

        result_r += RouteParam(
            'id',
            apis = {
                Method.Get: Api(SimpleTask)
            }
        )

        return result_r
