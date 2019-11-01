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

.. py:class:: Client2019POC
    
    .. py:method:: submit()
        :property:

        Provides route to submit a 3MF file for smart slicing

        .. py:method:: post(threemf_data)
            
            :param bytes threemf_data: 3MF file data
            :return: New task
            :rtype: SimpleTask

            Submits the 3MF for a new smart slice and returns the new task information

    
    .. py:method:: status()
        :property:

        Provides route to retrieve status of existing tasks

        .. py:method:: get(id=task_id)
            
            :param str task_id: Task Id
            :return: Task information
            :rtype: SimpleTask

            Retrieves the update task information, including the status, but does not include
            the results.

    .. py:method:: result()
        :property:

        Provides route to retrieve the results of a finished task

        .. py:method:: get(id=task_id)
            
            :param str task_id: Task Id
            :return: Task information, including results
            :rtype: SimpleTask

            Retrieves the update task information, including the results

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

.. autoclass:: SimpleTask

Thor HTTP Client Example
------------------------

.. literalinclude:: examples/thor-http-client.py

Thor HTTP Client 2019 POC Example
---------------------------------
.. literalinclude:: examples/thor-http-client-poc.py

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
