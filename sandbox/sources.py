# -*- coding: utf-8 -*-

"""
sandbox.sources
~~~~~~~~~~~~~~~

This module implements :class:`Application` which is the counterpart of
:class:`builder.Builder <udotcloud.builder.builder.Builder>`.
"""

import contextlib
import copy
import gevent
import gevent.subprocess
import itertools
import json
import logging
import os
import pkg_resources
import pprint
import re
import shutil
import signal
import socket
import tempfile
import time
import yaml

from .. import builder
from .buildfile import load_build_file
from .containers import ImageRevSpec, Image
from .exceptions import UnkownImageError
from .tarfile import Tarball
from ..utils import strsignal

class Application(object):
    """Represents a dotCloud application.

    :param root: source directory of the application.
    :param env: additional environment variables to define for this application.
    """

    def __init__(self, root, env):
        self._root = root
        #: Name of the application
        self.name = os.path.basename(os.path.abspath(root))
        username = os.environ.get("USER", "undefined")
        #: Environment for the application
        self.environment = {
            "DOTCLOUD_PROJECT": self.name,
            "DOTCLOUD_ENVIRONMENT": "default",
            "DOTCLOUD_FLAVOR": "microsandbox",
            "DOTCLOUD_USERNAME": username,
            "DOTCLOUD_EMAIL": os.environ.get(
                "EMAIL", "{0}@{1}".format(username, socket.getfqdn())
            )
        }
        self.environment.update(env)
        with open(os.path.join(self._root, "dotcloud.yml"), "r") as yml:
            self._build_file = load_build_file(yml.read())
        #: List of :class:`Service` in the application
        self.services = [
            Service(self, name, definition)
            for name, definition in self._build_file.iteritems()
        ]
        self._buildable_services = [s for s in self.services if s.buildable]

    def __str__(self):
        return "{0}: {1}".format(self.name, pprint.pformat(self._build_file))

    @staticmethod
    @contextlib.contextmanager
    def _build_dir():
        build_dir = tempfile.mkdtemp(prefix="dotcloud-")
        yield build_dir
        shutil.rmtree(build_dir, ignore_errors=True)

    def _generate_application_tarball(self, app_build_dir):
        logging.debug("Archiving {0} in {1}".format(self.name, app_build_dir))
        app_tarball = Tarball.create_from_files(
            ".",
            os.path.join(app_build_dir, "application.tar"),
            self._root
        )
        app_tarball.wait()
        sandbox_sdist = os.path.join(app_build_dir, "udotcloud.sandbox.tar.gz")
        shutil.copy(
            pkg_resources.resource_filename(
                "udotcloud.sandbox",
                "../dist/udotcloud.sandbox.tar.gz"
            ),
            sandbox_sdist
        )
        bootstrap_script = os.path.join(app_build_dir, "bootstrap.sh")
        shutil.copy(
            pkg_resources.resource_filename(
                "udotcloud.sandbox", "../builder/bootstrap.sh"
            ),
            bootstrap_script
        )

        return [app_tarball.dest, sandbox_sdist, bootstrap_script]

    def build(self, base_image=None):
        """Build the application using Docker.

        :return: a dictionnary with the service names in keys and the resulting
                 Docker images in values. Returns an empty dictionnary if there
                 is no buildable service in this application (i.e: only
                 databases). Returns None if one service couldn't be built.
        """

        if not self._buildable_services:
            return {}

        if not base_image:
            # TODO: design something to automatically pick a base image.
            logging.error(
                "You need to specify the base image to use via the -i option "
                "(you can pull and try lopter/sandbox-base)"
            )
            return

        with self._build_dir() as build_dir:
            app_files = self._generate_application_tarball(build_dir)
            logging.debug("Starting parallel build for {0} services".format(
                len(self._buildable_services)
            ))
            greenlets = [
                gevent.spawn(s.build, build_dir, app_files, base_image)
                for s in self._buildable_services
            ]
            gevent.joinall(greenlets)
            for service, result in zip(self._buildable_services, greenlets):
                try:
                    if not result.get():
                        return None
                except Exception:
                    logging.exception("Couldn't build service {0} ({1})".format(
                        service.name, service.type
                    ))
                    return None

        return {s.name: s.result_image for s in self.services}

    def run(self):
        """Run the application in Docker using the result of the latest build.

        :raises: :class:`~udotcloud.sandbox.exceptions.UnkownImageError` if the
                 application wasn't correctly built.

        .. note::

           Only buildable services are run, databases won't be started.
           Moreover, keep in mind that postinstall has not been executed during
           the build (postinstall expects to have the databases running).
        """

        def signal_handler(signum):
            logging.info("{0} caught, stopping {1} services…".format(
                strsignal(signum), len(greenlets)
            ))
            gevent.joinall([gevent.spawn(service.stop) for service in services])

        services = [service for service in self._buildable_services]
        greenlets = [gevent.spawn(service.run) for service in services]
        # FIXME: If one greenlet dies early (because the service doesn't run),
        # we will stay blocked here waiting on the other services to terminate.
        # So, we need to find a way to catch the error asap, maybe we could do
        # that with an Event + a series of Greenlet.get(block=False)?
        sigterm_handler = gevent.signal(signal.SIGTERM, signal_handler)
        try:
            gevent.joinall(greenlets)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT)
        finally:
            gevent.signal(signal.SIGTERM, sigterm_handler)

        for service, result in zip(self._buildable_services, greenlets):
            try:
                result.get()
            except UnkownImageError:
                logging.error(
                    "Couldn't find the image to run for service {0} ({1}), did "
                    "you build it?".format(service.name, service.type)
                )
                return False
            except Exception:
                logging.exception("Couldn't run service {0} ({1})".format(
                    service.name, service.type
                ))
                return False
        return True

class Service(object):
    """Represents a single service within a dotCloud application."""

    CUSTOM_PORTS_RANGE_START = 42800

    def __init__(self, application, name, definition):
        self._application = application
        self.name = name
        self.result_image = None
        for k, v in definition.iteritems():
            setattr(self, k, v)
        # I don't really know what happens in the yaml library but looks like
        # it does some caching and if we don't copy the environment here, the
        # modified version will leak accross unit tests:
        self.environment = copy.copy(self.environment)
        self.environment["DOTCLOUD_SERVICE_NAME"] = self.name
        self.environment["DOTCLOUD_SERVICE_ID"] = 0
        # Let's keep it as real dict too, so we can easily dump it:
        self._definition = definition
        self._definition['environment'] = self.environment
        self._extract_path = "/home/dotcloud"
        if self.type == "custom":
            self._extract_path = "/tmp"
        # TODO: actually build a list of services which are buildable or not,
        # once we have merged "builder" back in the same application that
        # should be easy since we will have access to builder.services.
        self.buildable = bool(builder.services.get_service_class(self.type))
        # "Allocate" the custom ports we are going to bind too inside the
        # container
        self._allocate_custom_ports()
        self._container = None

    # XXX This is half broken right now, since we will loose the original
    # protocol of the port (tcp or udp), anyway good enough for now (docker
    # doesn't support udp ports anyway).
    def _allocate_custom_ports(self):
        http_ports_count = self.ports.values().count("http")
        if (not re.match(r"^(custom|.+worker)$", self.type) and http_ports_count) \
            or ("worker" in self.type and http_ports_count > 1):
            logging.warning(
                "A http port was already defined for service "
                "{0} ({1})".format(self.name, self.type)
            )

        ports = {}
        port_number = self.CUSTOM_PORTS_RANGE_START
        for name, proto in self.ports.iteritems():
            ports[name] = str(port_number)
            port_number += 1
        self.ports = ports

    def _result_revspec(self):
        return ImageRevSpec.parse("{0}-{1}:ts-{2}".format(
            self._application.name, self.name, int(time.time())
        ))

    @property
    def _latest_result_revspec(self):
        return ImageRevSpec.parse("{0}-{1}:latest".format(
            self._application.name, self.name
        ))

    def _build_revspec(self):
        return ImageRevSpec(None, None, None, None) # keep build rev anonymous

    def _generate_environment_files(self, svc_build_dir):
        # environment.{json,yml} + .dotcloud_profile
        env_json = os.path.join(svc_build_dir, "environment.json")
        env_yml = os.path.join(svc_build_dir, "environment.yml")
        env_profile = os.path.join(svc_build_dir, "dotcloud_profile")
        env = {
            key: value for key, value in itertools.chain(
                self._application.environment.iteritems(),
                self.environment.iteritems()
            )
        }
        env.update({
            "PORT_{0}".format(name.upper()): port
            for name, port in self.ports.iteritems()
        })
        with open(env_json, 'w') as fp:
            json.dump(env, fp, indent=4)
        with open(env_yml, 'w') as fp:
            yaml.safe_dump(env, fp, indent=4, default_flow_style=False)
        with open(env_profile, 'w') as fp:
            fp.writelines([
                "export {0}={1}\n".format(k, v) for k, v in env.iteritems()
            ])
        return [env_json, env_yml, env_profile]

    def _dump_service_definition(self, svc_build_dir):
        definition = os.path.join(svc_build_dir, "definition.json")
        with open(definition, "w") as fp:
            json.dump(dict(self._definition, name=self.name), fp, indent=4)
        return definition

    def _generate_service_tarball(self, app_build_dir, app_files):
        svc_build_dir = os.path.join(app_build_dir, self.name)
        os.mkdir(svc_build_dir)
        svc_tarball_name = "service.tar"
        app_files_names = [os.path.basename(path) for path in app_files]

        svc_files = self._generate_environment_files(svc_build_dir)
        svc_files.append(self._dump_service_definition(svc_build_dir))
        svc_tarball = Tarball.create_from_files(
            [os.path.basename(path) for path in svc_files],
            os.path.join(svc_build_dir, svc_tarball_name),
            svc_build_dir
        )
        svc_tarball.wait()

        for name, path in zip(app_files_names, app_files):
            os.link(path, os.path.join(svc_build_dir, name))
        app_files_names.append(svc_tarball_name)
        svc_tarball = Tarball.create_from_files(
            app_files_names,
            os.path.join(app_build_dir, "{0}.tar".format(self.name)),
            svc_build_dir
        )
        svc_tarball.wait()
        return svc_tarball

    def _unpack_service_tarball(self, svc_tarball_path, container):
        logging.debug("Extracting code in service {0}".format(self.name))
        with open(svc_tarball_path, "r") as source:
            tar_extract = ["tar", "-xf", "-", "-C", self._extract_path]
            with container.run(tar_extract, stdin=container.PIPE) as dest:
                buf = source.read(8192)
                while buf:
                    dest.stdin.write(buf)
                    buf = source.read(8192)
                dest.stdin.close()

    def build(self, app_build_dir, app_files, base_image):
        logging.info("Building service {0}…".format(self.name))
        svc_tarball = self._generate_service_tarball(app_build_dir, app_files)
        logging.debug("Tarball for service {0} generated at {1}".format(
            self.name, svc_tarball.dest
        ))
        # Upload all the code:
        self._container = base_image.instantiate(
            commit_as=self._build_revspec()
        )
        self._unpack_service_tarball(svc_tarball.dest, self._container)
        # Install the builder via the bootstrap script
        self._container = self._container.result.instantiate(
            commit_as=self._build_revspec()
        )
        bootstrap_script = os.path.join(self._extract_path, "bootstrap.sh")
        with self._container.run([bootstrap_script]):
            logging.debug("Installing builder in service {0}".format(self.name))
        logging.debug("Builder bootstrap logs:\n{0}".format(
            self._container.logs
        ))
        if self._container.exit_status != 0:
            logging.warning(
                "Couldn't install the builder in service {0} (bootstrap script "
                "returned {1}".format(self.name, self._container.exit_status)
            )
        # And run it
        self._container = self._container.result.instantiate(
            commit_as=self._result_revspec()
        )
        # Since we don't actually go through login(1) we need to set HOME
        # otherwise, .profile won't be executed by login shells:
        with self._container.run(
            [builder.BUILDER_INSTALL_PATH, self._extract_path],
            env={"HOME": "/home/dotcloud"}, as_user="dotcloud"
        ):
            logging.debug("Running builder in service {0}".format(self.name))
        logging.info("Build logs for {0}:\n{1}".format(
            self.name, self._container.logs
        ))
        if self._container.exit_status != 0:
            logging.error(
                "The build failed on service {0}: the builder returned {1} "
                "(expected 0)".format(self.name, self._container.exit_status)
            )
            return False
        self.result_image = self._container.result
        self.result_image.add_tag("latest")
        self._container = None
        return True

    def run(self):
        image = Image(self._latest_result_revspec)
        self._container = image.instantiate()
        ports = self.ports.values()
        ports.append(22)
        if not "worker" in self.type:
            ports.append(80)
        supervisor_conf = os.path.join(self._extract_path, "supervisor.conf")
        logging.info("Starting Supervisor in {0}".format(image))
        with self._container.run_stream_logs(
            ["supervisord", "-n", "-c", supervisor_conf],
            env={"HOME": "/home/dotcloud"},
            as_user="dotcloud",
            ports=ports
        ) as supervisor:
            for port, mapped_port in supervisor.ports.iteritems():
                logging.info(
                    "Port {0} on service {1} mapped to {2} on the "
                    "Docker host".format(port, self.name, mapped_port)
                )
        logging.info("Service {0} exited".format(self.name))
        self._container = None

    def stop(self):
        """If the service is currently running or building, interrupt it."""

        if self._container:
            self._container.stop()
