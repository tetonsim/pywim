import pika
import json
import uuid
import threading
import time

class ConnectionMaker:
    def __init__(self, connection_class, url, queue_produce=None, queue_consume=None):
        self.connection_class = connection_class
        self.url = url
        self.queue_produce = queue_produce if queue_produce else 'simd-in'
        self.queue_consume = queue_consume if queue_consume else 'simd-out'

    def __call__(self, queue_produce=None, queue_consume=None):
        p = queue_produce if queue_produce else self.queue_produce
        c = queue_consume if queue_consume else self.queue_consume
        return self.connection_class(self.url, p, c)

class Connection:
    def __init__(self, url, queue_produce, queue_consume):
        self._connection = pika.BlockingConnection(
            pika.URLParameters(url=url)
        )

        self._queue_produce = queue_produce
        self._queue_consume = queue_consume

        self._channel = self._connection.channel()

        self._channel.queue_declare(self._queue_produce)
        self._channel.queue_declare(self._queue_consume)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @staticmethod
    def _make_id(id=None):
        if id is None:
            id = str(uuid.uuid4()).replace('-', '')

        if not isinstance(id, str):
            id = str(id)

        return id

    def close(self):
        if self._connection.is_open:
            self._connection.close()

    def purge(self):
        self._channel.queue_purge(self._queue_produce)
        self._channel.queue_purge(self._queue_consume)

    def publish(self, content, id=None):
        raise NotImplementedError()

class SimpleConnection(Connection):
    def __init__(self, *args, **kwargs):
        raise Exception('SimpleConnection deprecated in 19.0.24')

class DirectReplyConnection(Connection):
    QUEUE_REPLY = 'amq.rabbitmq.reply-to'

    def __init__(self, url, queue_produce, queue_consume):
        super().__init__(url, queue_produce, DirectReplyConnection.QUEUE_REPLY)

        self._response = None

        self._channel.basic_consume(
            queue=DirectReplyConnection.QUEUE_REPLY,
            auto_ack=True,
            on_message_callback=self._consume
        )

    def _consume(self, channel, method, properties, body):
        dbody = json.loads(body)

        self._response = dbody

        channel.close()

    def publish(self, content, id=None, callback=None):
        id = Connection._make_id(id)

        dbody = {
            'id': id,
            'content': content
        }

        self._response = None

        self._channel.basic_publish(
            exchange = '',
            routing_key = self._queue_produce,
            body = json.dumps(dbody),
            properties=pika.BasicProperties(
                reply_to=DirectReplyConnection.QUEUE_REPLY,
                correlation_id=id
            )
        )

        return id

    def get(self):
        self._channel.start_consuming()
        return self._response
