#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

from flask import Flask, make_response

logging.basicConfig(level="DEBUG")

app = Flask(__name__)
app.debug = False

@app.before_first_request
def configure_logging():
    if not app.debug:
        stderr_logger = logging.StreamHandler()
        stderr_logger.setLevel(logging.DEBUG)
        app.logger.addHandler(stderr_logger)
        app.logger.setLevel(logging.DEBUG)

@app.route("/", methods=["GET"])
def hello():
    return make_response("</br>\n".join([
        "{0}={1}".format(k, v) for k, v in os.environ.iteritems()
    ]))
