# -*- coding: utf-8 -*-

import contextlib
import errno
import json
import logging
import os
import subprocess

from .services import get_service

@contextlib.contextmanager
def _ignore_eexist():
    try:
        yield
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            raise

class Builder(object):

    def __init__(self, build_dir):
        self._build_dir = build_dir
        self._code_dir = os.path.join(build_dir, "code")
        self._current_dir = os.path.join(build_dir, "current")
        self._app_tarball = os.path.join(build_dir, "application.tar")
        self._svc_tarball = os.path.join(build_dir, "service.tar")

    def _unpack_sources(self):
        logging.debug("Extracting application.tar and service.tar")
        with _ignore_eexist():
            os.mkdir(self._code_dir)
        untar_app = subprocess.Popen([
            "tar", "--recursive-unlink",
            "-xf", self._app_tarball,
            "-C", self._code_dir,
        ])
        untar_svc = subprocess.Popen([
            "tar",
            "-xf", self._svc_tarball,
            "-C", self._build_dir
        ])
        untar_svc = untar_svc.wait()
        untar_app = untar_app.wait()
        if untar_svc != 0:
            logging.error(
                "Couldn't extract the environment and the supervisor "
                "configuration (tar returned {0})".format(untar_svc)
            )
        else:
            os.unlink(self._svc_tarball)
        if untar_app != 0:
            logging.error(
                "Couldn't extract the application code "
                "(tar returned {0})".format(untar_app)
            )
        else:
            os.unlink(self._app_tarball)
        if untar_app or untar_svc:
            return False

        definition = os.path.join(self._build_dir, "definition.json")
        logging.debug("Loading service definition from {0}".format(definition))
        with open(definition, "r") as fp:
            self._svc_definition = json.load(fp)
        os.unlink(definition)
        self._approot_dir = os.path.join(
            self._code_dir, self._svc_definition['approot']
        )

        logging.debug("Symlinking current from {0}".format(
            self._approot_dir, self._current_dir
        ))
        with _ignore_eexist():
            os.symlink(self._approot_dir, self._current_dir)

        return True

    def build(self):
        if not self._unpack_sources():
            return False
        service_builder = get_service(
            self._build_dir, self._current_dir, self._svc_definition
        )
        service_builder.build()
