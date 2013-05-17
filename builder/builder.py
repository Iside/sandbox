# -*- coding: utf-8 -*-

"""
builder.builder
~~~~~~~~~~~~~~~

This module implements :class:`Builder` which is the counter part of
:class:`sandbox.Application <udotcloud.sandbox.sources.Application>`.
"""

import errno
import json
import logging
import os
import shutil
import subprocess

from .services import get_service
from ..utils import ignore_eexist
from ..utils.debug import log_success

class Builder(object):
    """Build a service in Docker, from the tarball uploaded by `Sandbox`_.

    :param build_dir: path to the directory where the “application.tar” and
                      “service.tar” tarball can be found.
    """

    def __init__(self, build_dir):
        self._build_dir = build_dir
        self._code_dir = os.path.join(build_dir, "code")
        self._current_dir = os.path.join(build_dir, "current")
        self._app_tarball = os.path.join(build_dir, "application.tar")
        self._svc_tarball = os.path.join(build_dir, "service.tar")

    def _unpack_sources(self):
        logging.debug("Extracting application.tar and service.tar")
        with ignore_eexist():
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

        logging.debug("Setting up SSH keys")
        ssh_dir = os.path.join(self._build_dir, ".ssh")
        try:
            os.mkdir(ssh_dir, 0700)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise
        try:
            os.unlink(os.path.join(ssh_dir, "authorized_keys2"))
        except OSError as ex:
            if ex.errno != errno.ENOENT:
                raise
        shutil.move(os.path.join(self._build_dir, "authorized_keys2"), ssh_dir)

        definition = os.path.join(self._build_dir, "definition.json")
        logging.debug("Loading service definition from {0}".format(definition))
        with open(definition, "r") as fp:
            self._svc_definition = json.load(fp)
        os.unlink(definition)

        return True

    def build(self):
        """Unpack the sources and start the build.

        The build is started using the right service class from
        :mod:`builder.services <udotcloud.builder.services>`.
        """

        if not self._unpack_sources():
            return False
        service_builder = get_service(
            self._build_dir, self._current_dir, self._svc_definition
        )
        returncode = service_builder.build()
        if returncode == 0:
            log_success("{0} build done for service {1}".format(
                self._svc_definition['type'], self._svc_definition['name']
            ))
        return returncode
