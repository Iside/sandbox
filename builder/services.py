# -*- coding: utf-8 -*-

import logging
import os
import subprocess

from ..utils import strsignal

class ServiceBase(object):

    def __init__(self, build_dir, svc_dir, definition):
        self._build_dir = build_dir
        self._svc_dir = svc_dir
        self._type = definition["type"]
        self._name = definition["name"]
        self._config = definition.get("config", {})
        self._extra_requirements = definition.get("requirements", [])
        self._prebuild_script = definition.get("prebuild")
        self._postbuild_script = definition.get("postbuild")

    def _configure(self): pass
    def _install_requirements(self): pass

    def _run_hook(self, hook_script):
        subprocess.check_call(
            "chmod +x {0} >/dev/null 2>&1; exec {0}".format(hook_script),
            cwd=self._svc_dir,
            shell=True
        )

    def _hook_prebuild(self):
        if self._prebuild_script:
            self._run_hook(self._prebuild_script)

    def _hook_postbuild(self):
        if self._postbuild_script:
            self._run_hook(self._postbuild_script)

    def build(self):
        logging.debug("Building service {0} ({1}) inside Docker".format(
            self._name, self._type
        ))
        try:
            self._hook_prebuild()
            self._configure()
            self._install_requirements()
            self._hook_postbuild()
        except subprocess.CalledProcessError as ex:
            msg = "Can't build service {0} ({1}): the command " \
                "`{2}` ".format(self._name, self._type, " ".join(ex.cmd))
            if ex.returncode < 0:
                signum = -ex.returncode
                logging.error(msg + "exited on signal {0} ({1})".format(
                    signum, strsignal(signum)
                ))
            elif ex.returncode == 127:
                logging.error(msg + "was not found")
            else:
                logging.error(msg + "returned {0}".format(ex.returncode))
            return False
        return True

class PythonWorker(ServiceBase):

    def __init__(self, *args, **kwargs):
        ServiceBase.__init__(self, *args, **kwargs)
        self._virtualenv_dir = os.path.join(self._build_dir, "env")
        self._pip = os.path.join(self._virtualenv_dir, "bin", "pip")
        self._pip_cache = os.path.join(self._build_dir, ".pip-cache")
        self._profile = os.path.join(self._build_dir, "dotcloud_profile")
        self._requirements = os.path.join(self._svc_dir, "requirements.txt")
        self._svc_setup_py = os.path.join(self._svc_dir, "setup.py")

    def _configure(self):
        python_version = self._config.get("python_version", "v2.6")[1:]
        logging.info("Configuring {0} ({1}) for Python {2}:".format(
            self._name, self._type, python_version
        ))
        python_version = "python" + python_version
        subprocess.check_call([
            "virtualenv", "-p", python_version, self._virtualenv_dir
        ])
        with open(self._profile, 'a') as profile:
            profile.write("\n. {0}\n".format(
                os.path.join(self._virtualenv_dir, "bin/activate")
            ))

    def _install_requirements(self):
        if os.path.exists(self._requirements):
            logging.info("Installating requirements from requirements.txt:")
            subprocess.check_call([
                self._pip, "install",
                "--download-cache={0}".format(self._pip_cache),
                "-r", self._requirements
            ])
        if self._extra_requirements:
            logging.info(
                "Installating extra requirements from dotcloud.yml: "
                "{0}".format(", ".join(self._extra_requirements))
            )
            subprocess.check_call([
                self._pip, "install",
                "--download-cache={0}".format(self._pip_cache),
                " ".join(self._extra_requirements)
            ])
        if os.path.exists(self._svc_setup_py):
            subprocess.check_call(
                [self._pip, "install", ".", "-U"],
                cwd=self._svc_dir
            )

class Python(PythonWorker):

    def _configure(self):
        PythonWorker._configure(self)
        # TODO: setup the uwsgi configuration for supervisor

def get_service(build_dir, svc_dir, svc_definition):
    service_class = {
        "python-worker": PythonWorker
    }.get(svc_definition['type'])
    if not service_class:
        raise ValueError("No builder defined for {0} services".format(
            svc_definition['type']
        ))
    return service_class(build_dir, svc_dir, svc_definition)
