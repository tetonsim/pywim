import pika
import json
import uuid

class ConnectionMaker(object):
    def __init__(self, connection_class, url, queue_produce=None, queue_consume=None):
        self.connection_class = connection_class
        self.url = url
        self.queue_produce = queue_produce if queue_produce else 'simd-in'
        self.queue_consume = queue_consume if queue_consume else 'simd-out'

    def __call__(self, queue_produce=None, queue_consume=None):
        p = queue_produce if queue_produce else self.queue_produce
        c = queue_consume if queue_consume else self.queue_consume
        return self.connection_class(self.url, p, c)

class SimpleConnection(object):
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

    def close(self):
        if self._connection.is_open:
            self._connection.close()

    def purge(self):
        self._channel.queue_purge(self._queue_produce)
        self._channel.queue_purge(self._queue_consume)

    def publish(self, content, id=None):
        if id is None:
            id = str(uuid.uuid4()).replace('-', '')

        if not isinstance(id, str):
            id = str(id)

        dbody = {
            'id': id,
            'content': content
        }

        self._channel.basic_publish(
            exchange = '',
            routing_key = self._queue_produce,
            body = json.dumps(dbody)
        )

        return id

    def get(self, id=None):
        method, properties, body = self._channel.basic_get(self._queue_consume)

        if method is None:
            return None

        msg_consumed = True

        if body is not None:
            try:
                dbody = json.loads(body)
            except:
                msg_consumed = False
                return None
        
        if msg_consumed:
            if id is None:
                self._channel.basic_ack(method.delivery_tag)
            else:
                if id == dbody['id']:
                    self._channel.basic_ack(method.delivery_tag)
                else:
                    self._channel.basic_nack(method.delivery_tag)
                    return None

        return dbody
