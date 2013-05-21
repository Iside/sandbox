# -*- coding: utf-8 -*-

import json
import logging
import os
import redis
import sys
import zerorpc

class API(object):

    def __init__(self, redis_url):
        self._redis = redis.StrictRedis.from_url(redis_url, db=0)

    def enqueue(self, value):
        """Enqueue the given value in Redis.

        The value has to be serializable in JSON.
        """

        self._redis.lpush("queue", json.dumps(value))
        return "ok"

    def dequeue(self):
        """Dequeue a value and return it."""

        return self._redis.rpop("queue")

if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    if "DOTCLOUD_DB_REDIS_URL" not in os.environ:
        logging.error("You need to set `DOTCLOUD_DB_REDIS_URL` in the environment")
        sys.exit(1)
    server = zerorpc.Server(API(os.environ['DOTCLOUD_DB_REDIS_URL']))
    logging.info("Binding zeroservice on {0}".format(os.environ['PORT_ZEROSERVICE']))
    server.bind("tcp://0.0.0.0:{0}".format(os.environ['PORT_ZEROSERVICE']))
    server.run()
