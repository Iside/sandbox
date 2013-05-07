# -*- coding: utf-8 -*-

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
import shutil
import socket
import tempfile
import time
import yaml

from .buildfile import load_build_file
from .containers import ImageRevSpec, Image
from .exceptions import UnkownImageError
from .tarfile import Tarball
from ..builder import BUILDER_INSTALL_PATH

class Application(object):

    def __init__(self, root, env):
        self._root = root
        self.name = os.path.basename(root)
        username = os.environ.get("USER", "undefined")
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
        if not self._buildable_services:
            return {}

        if not base_image:
            # TODO: design something to automatically pick a base image.
            logging.error(
                "You need to specify the base image to use via the -i option"
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
                    result.get()
                except Exception:
                    logging.exception("Couldn't build service {0} ({1})".format(
                        service.name, service.type
                    ))
                    return None

        return {s.name: s.result_image for s in self.services}

    def run(self):
        # TODO: install a specific SIGINT handler here?
        greenlets = [gevent.spawn(s.run) for s in self._buildable_services]
        # FIXME: If one greenlet dies early (because the service doesn't run),
        # we will stay blocked here waiting on the other services to terminate.
        # So, we need to find a way to catch the error asap, maybe we could do
        # that with an Event + a series of Greenlet.get(block=False)?
        gevent.joinall(greenlets)
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

    CUSTOM_PORTS_RANGE_START = 42800

    def __init__(self, application, name, definition):
        self._application = application
        self._extract_path = "/home/dotcloud"
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
        # TODO: actually build a list of services which are buildable or not,
        # once we have merged "builder" back in the same application that
        # should be easy since we will have access to builder.services.
        self.buildable = True
        # "Allocate" the custom ports we are going to bind too inside the
        # container
        self._allocate_custom_ports()

    # XXX This is half broken right now, since we will loose the original
    # protocol of the port (tcp or udp), anyway good enough for now (docker
    # doesn't support udp ports anyway).
    def _allocate_custom_ports(self):
        http_ports_count = self.ports.values().count("http")
        if ("worker" in self.type and http_ports_count > 1) \
            or ("worker" not in self.type and http_ports_count):
            logging.warning(
                "You cannot define more than one http port per service!"
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
        return env_json, env_yml, env_profile

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

        self._generate_environment_files(svc_build_dir)
        self._dump_service_definition(svc_build_dir)
        svc_tarball = Tarball.create_from_files(
            ".",
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
        container = base_image.instantiate(commit_as=self._build_revspec())
        self._unpack_service_tarball(svc_tarball.dest, container)
        # Install the builder via the bootstrap script
        container = container.result.instantiate(
            commit_as=self._build_revspec()
        )
        bootstrap_script = os.path.join(self._extract_path, "bootstrap.sh")
        with container.run([bootstrap_script]):
            logging.debug("Installing builder in service {0}".format(self.name))
        logging.debug("Builder bootstrap logs:\n{0}".format(container.logs))
        # And run it
        container = container.result.instantiate(
            commit_as=self._result_revspec()
        )
        with container.run(
            [BUILDER_INSTALL_PATH, self._extract_path], as_user="dotcloud"
        ):
            logging.debug("Running builder in service {0}".format(self.name))
        logging.info("Build logs for {0}:\n{1}".format(
            self.name, container.logs
        ))
        self.result_image = container.result
        self.result_image.add_tag("latest")

    def run(self):
        image = Image(self._latest_result_revspec)
        container = image.instantiate()
        ports = self.ports.values()
        ports.append(22)
        if not "worker" in self.type:
            ports.append(80)
        supervisor_conf = os.path.join(self._extract_path, "supervisor.conf")
        logging.info("Starting Supervisor in {0}".format(image))
        # Since we don't actually go through login(1) we do need to set HOME
        # otherwise, .profile won't be executed event though we start the
        # daemon defined in supervisor via sh -l:
        with container.run_stream_logs(
            ["supervisord", "-n", "-c", supervisor_conf],
            env={"HOME": "/home/dotcloud"},
            as_user="dotcloud",
            ports=ports
        ) as container:
            for port, mapped_port in container.ports.iteritems():
                logging.info(
                    "Port {0} on service {1} mapped to {2} on the "
                    "Docker host".format(port, self.name, mapped_port)
                )
        logging.info("Service {0} exited".format(self.name))
