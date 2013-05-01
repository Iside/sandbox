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
from .containers import ImageRevSpec
from .tarfile import Tarball
from .version import __version__

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
        builder_sdist = os.path.join(app_build_dir, "udotcloud.builder.tar.gz")
        shutil.copy(
            pkg_resources.resource_filename(
                "udotcloud.sandbox",
                "../builder/dist/udotcloud.builder-{0}.tar.gz".format(
                    __version__
                )
            ),
            builder_sdist
        )
        bootstrap_script = os.path.join(app_build_dir, "bootstrap.sh")
        shutil.copy(
            pkg_resources.resource_filename(
                "udotcloud.sandbox", "../builder/bootstrap.sh"
            ),
            bootstrap_script
        )

        return [app_tarball.dest, builder_sdist, bootstrap_script]

    def build(self, base_image=None):
        buildable_services = [s for s in self.services if s.buildable]
        if not buildable_services:
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
                len(buildable_services)
            ))
            greenlets = [
                gevent.spawn(s.build, build_dir, app_files, base_image)
                for s in buildable_services
            ]
            gevent.joinall(greenlets)
            for service, result in zip(buildable_services, greenlets):
                try:
                    result.get()
                except Exception:
                    logging.exception("Couldn't build service {0} ({1})".format(
                        service.name, service.type
                    ))
                    return None

        return {s.name: s.result_image for s in self.services}

    def run(self):
        pass

class Service(object):

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
        # TODO: actually build a list of services which are buildable or not:
        self.buildable = True

    def _result_revspec(self):
        return ImageRevSpec.parse("{0}-{1}:ts-{2}".format(
            self._application.name, self.name, int(time.time())
        ))

    def _build_revspec(self):
        return ImageRevSpec(None, None, None, None) # keep build rev anonymous

    def _generate_supervisor_include(self, svc_build_dir):
        PROGRAM_TEMPLATE = """[program:{name}]
command=/bin/sh -lc "exec {command}"
directory={directory}
stdout_logfile=/var/log/supervisor/{name}.log
stderr_logfile=/var/log/supervisor/{name}_error.log

"""
        supervisor_include = os.path.join(svc_build_dir, "supervisor.conf")
        exec_dir = "/home/dotcloud"
        if self.type != "custom":
            exec_dir = os.path.join(exec_dir, "current")
        with open(supervisor_include, 'w') as fp:
            if self.processes:
                for name, command in self.processes.iteritems():
                    fp.write(PROGRAM_TEMPLATE.format(
                        name=name, command=command, directory=exec_dir
                    ))
            elif self.process:
                fp.write(PROGRAM_TEMPLATE.format(
                    name=self.name, command=self.process, directory=exec_dir
                ))
            elif self.type == "custom":
                fp.write(PROGRAM_TEMPLATE.format(
                    name=self.name, command="~/run", directory=exec_dir
                ))
        return supervisor_include

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
            json.dump(self._definition, fp, indent=4)
        return definition

    def _generate_service_tarball(self, app_build_dir, app_files):
        svc_build_dir = os.path.join(app_build_dir, self.name)
        os.mkdir(svc_build_dir)
        svc_tarball_name = "service.tar"
        app_files_names = [os.path.basename(path) for path in app_files]

        self._generate_supervisor_include(svc_build_dir)
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
        # XXX: should be a constant in the builder package:
        dotcloud_builder_path = "/var/lib/dotcloud/builder/bin/dotcloud-builder"
        with container.run(
            [dotcloud_builder_path, self._extract_path], as_user="dotcloud"
        ):
            logging.debug("Running builder in service {0}".format(self.name))
        logging.debug("Build logs for {0}:\n{1}".format(
            self.name, container.logs
        ))
        self.result_image = container.result
