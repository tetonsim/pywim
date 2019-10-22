pywim.http package
==================

Submodules
----------

pywim.http.thor module
----------------------

.. py:module:: pywim.http.thor

.. py:class:: Client
    
    .. py:method:: auth()
        :property:

        Provides all auth routes

        .. py:attribute:: token

            Provides routes for retrieving and releasing auth tokens (login and logout).

            .. py:method:: post(credentials)
                
                :param LoginRequest credentials: Credentials
                :return: User and token information
                :rtype: UserAuth

                Requests a new auth token using the provided credentials. If a token is successfully
                retrieved it will be automatically stored in the client and used in subsequent requests.
                An exception is raised if the provided credentials are invalid.

            .. py:method:: delete()

                :return: Token delete status
                :rtype: dict

        .. py:attribute:: whoami

            Provides routes to query information about the user associated with the stored token.

            .. py:method:: get()

                :return: User and token information
                :rtype: UserAuth

.. autoclass:: LoginRequest

.. autoclass:: User

.. autoclass:: Token

.. autoclass:: UserAuth

.. autoclass:: TaskStatus
    :members:
    :undoc-members:

.. autoclass:: NewTask

.. autoclass:: Task

.. autoclass:: TaskSubmission

.. autoclass:: AssetUrl

.. literalinclude:: examples/thor-http-client.py

pywim.http.wim module
---------------------

.. py:module:: pywim.http.wim


Module contents
---------------

.. py:module:: pywim.http
   
.. autoexception:: WimHttpException

.. autoexception:: ClientException
    :show-inheritance:

.. autoexception:: ServerException
    :show-inheritance:

    .. py:attribute:: response

        Server response as a requests.Response type

    .. py:attribute:: message

        String message about the exception
