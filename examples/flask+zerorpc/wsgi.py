# -*- coding: utf-8

import logging
import os
import redis
import sys

from flask import Flask, make_response

logging.basicConfig(level="DEBUG")

if "DOTCLOUD_DB_REDIS_URL" not in os.environ:
    logging.error("You need to set `DOTCLOUD_DB_REDIS_URL` in the environment")
    sys.exit(1)

app = Flask(__name__)
app.debug = False

redis = redis.StrictRedis.from_url(os.environ['DOTCLOUD_DB_REDIS_URL'])

@app.before_first_request
def configure_logging():
    if not app.debug:
        stderr_logger = logging.StreamHandler()
        stderr_logger.setLevel(logging.DEBUG)
        app.logger.addHandler(stderr_logger)
        app.logger.setLevel(logging.DEBUG)

@app.route("/", methods=["GET"])
def check_queue():
    return make_response("</br>\n".join([
        value for value in redis.lrange("queue", 0, -1)
    ]))

application = app
