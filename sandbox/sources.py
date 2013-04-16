# -*- coding: utf-8 -*-

import contextlib
import gevent
import itertools
import json
import logging
import os
import pprint
import shutil
import socket
import tempfile
import yaml

from .buildfile import load_build_file
from .tarfile import Tarball

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

    def build(self, base_image=None):
        with self._build_dir() as build_dir:
            logging.debug("Starting parallel build for {0} in {1}".format(
                self.name, build_dir
            ))
            app_tarball = Tarball.create_from_files(
                ".",
                os.path.join(build_dir, "application.tar"),
                self._root
            )
            app_tarball.wait()
            greenlets = [
                gevent.spawn(
                    service.build, build_dir, app_tarball.dest, base_image
                )
                for service in self.services
            ]
            gevent.joinall(greenlets)

class Service(object):

    def __init__(self, application, name, definition):
        self._application = application
        self.name = name
        for k, v in definition.iteritems():
            setattr(self, k, v)
        self.environment["DOTCLOUD_SERVICE_NAME"] = self.name
        self.environment["DOTCLOUD_SERVICE_ID"] = 0
        # TODO: actually build a list of services which are buildable or not:
        self.buildable = True

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

    def _generate_service_tarball(self, app_build_dir, app_tarball):
        svc_build_dir = os.path.join(app_build_dir, self.name)
        os.mkdir(svc_build_dir)
        svc_tarball_name = "service.tar"
        app_tarball_name = os.path.basename(app_tarball)

        self._generate_supervisor_include(svc_build_dir)
        self._generate_environment_files(svc_build_dir)
        svc_tarball = Tarball.create_from_files(
            ".",
            os.path.join(svc_build_dir, svc_tarball_name),
            svc_build_dir
        )
        svc_tarball.wait()

        os.link(app_tarball, os.path.join(svc_build_dir, app_tarball_name))
        svc_tarball = Tarball.create_from_files(
            [svc_tarball_name, app_tarball_name],
            os.path.join(app_build_dir, "{0}.tar".format(self.name)),
            svc_build_dir
        )
        svc_tarball.wait()
        return svc_tarball

    def build(self, app_build_dir, app_tarball, base_image):
        #image = Image("lopter/raring-base", "latest")
        #container = image.instantiate()
        #container.install_system_packages(self.systempackages)
        #image = container.commit("Installed system packages: {0}".format(
        #    " ".join(self.systempackages)
        #))
        logging.info("Building service {0}".format(self.name))
        svc_tarball = self._generate_service_tarball(app_build_dir, app_tarball)
        logging.debug("Tarball for service {0} generated at {1}".format(
            self.name, svc_tarball.dest
        ))
