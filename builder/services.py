# -*- coding: utf-8 -*-

"""
builder.services
~~~~~~~~~~~~~~~~

This module defines one class per service type. Each class knows how to build a
single type service. Use :func:`get_service` to get the right “builder” class
from a service type.
"""

import copy
import logging
import os
import shutil
import subprocess

from ..utils import ignore_eexist, strsignal

class ServiceBase(object):

    SUPERVISOR_PROCESS_TPL = """[program:{name}]
command=/bin/sh -lc "exec {command}"
directory={exec_dir}
stdout_logfile={supervisor_dir}/{name}.log
stderr_logfile={supervisor_dir}/{name}_error.log

"""

    def __init__(self, build_dir, svc_dir, definition):
        self._build_dir = build_dir
        self._svc_dir = svc_dir
        self._definition = definition
        self._type = definition['type']
        self._name = definition['name']
        self._processes = definition['processes']
        self._process = definition['process']
        self._config = definition.get("config", {})
        self._extra_requirements = definition.get("requirements", [])
        self._prebuild_script = definition.get("prebuild")
        self._postbuild_script = definition.get("postbuild")
        self._supervisor_dir = os.path.join(self._build_dir, "supervisor")
        self._supervisor_include = os.path.join(self._build_dir, "supervisor.conf")
        self._profile = os.path.join(self._build_dir, "dotcloud_profile")

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

    def _symlink_current(self):
        approot_dir = os.path.join(
            self._build_dir, "code", self._definition['approot']
        )
        # XXX
        logging.debug("Symlinking {1} from {0}".format(approot_dir, self._svc_dir))
        with ignore_eexist():
            os.symlink(approot_dir, self._svc_dir)

    def _generate_supervisor_configuration(self):
        # The configuration itself will be in ~dotcloud but put all the other
        # supervisor related files in a subdir:
        with ignore_eexist():
            os.mkdir(self._supervisor_dir)
        with open(self._supervisor_include, 'w') as fp:
            fp.write("""[supervisord]
logfile={supervisor_dir}/supervisord.log
pidfile={supervisor_dir}/supervisord.pid

[unix_http_server]
file={supervisor_dir}/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix://{supervisor_dir}/supervisor.sock

[include]
files=/home/dotcloud/current/supervisord.conf

""".format(supervisor_dir=self._supervisor_dir))

    def _generate_processes(self):
        with open(self._supervisor_include, "a") as fp:
            if self._processes:
                for name, command in self._processes.iteritems():
                    fp.write(self.SUPERVISOR_PROCESS_TPL.format(
                        name=name, command=command, exec_dir=self._svc_dir,
                        supervisor_dir=self._supervisor_dir
                    ))
            elif self._process:
                fp.write(self.SUPERVISOR_PROCESS_TPL.format(
                    name=self._name, command=self._process,
                    exec_dir=self._svc_dir, supervisor_dir=self._supervisor_dir
                ))

    def build(self):
        logging.debug("Building service {0} ({1}) inside Docker".format(
            self._name, self._type
        ))
        try:
            self._symlink_current()
            self._hook_prebuild()
            self._generate_supervisor_configuration()
            self._generate_processes()
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

class Custom(ServiceBase):

    SUPERVISOR_PROCESS_TPL = """[program:{name}]
command=/bin/bash -lc "[ -f ~/profile ] && . ~/profile; exec {command}"
directory={exec_dir}
stdout_logfile={supervisor_dir}/{name}.log
stderr_logfile={supervisor_dir}/{name}_error.log

"""

    def __init__(self, *args, **kwargs):
        ServiceBase.__init__(self, *args, **kwargs)
        self._svc_dir = self._build_dir
        self._supervisor_dir = "/home/dotcloud/supervisor"
        self._profile = os.path.join("/home/dotcloud/dotcloud_profile")
        self._buildscript = None
        if "buildscript" in self._definition:
            self._buildscript = os.path.join(
                self._build_dir, "code", self._definition['buildscript']
            )

    def _symlink_current(self): pass

    def _generate_processes(self):
        if self._processes or self._process:
            ServiceBase._generate_processes(self)
            return
        with open(self._supervisor_include, "a") as fp:
            fp.write(self.SUPERVISOR_PROCESS_TPL.format(
                name=self._name, command="~/run",
                exec_dir="/home/dotcloud", supervisor_dir=self._supervisor_dir
            ))

    def _configure(self):
        if not self._buildscript:
            return
        extra_env = copy.copy(os.environ)
        for k, v in self._definition.iteritems():
            k = k.upper()
            if isinstance(v, dict):
                for sk, sv in v.items():
                    extra_env['_'.join(('SERVICE', k, sk.upper()))] = str(sv)
            else:
                extra_env['SERVICE_' + k] = str(v)
        logging.info("Calling buildscript {0} for service {1} ({2})".format(
            self._definition['buildscript'], self._name, self._type
        ))
        subprocess.check_call(
            ["/bin/sh", "-lc", "exec {0}".format(self._buildscript)],
            cwd=os.path.join(self._build_dir, "code"), env=extra_env,
        )
        shutil.move(
            os.path.join(self._build_dir, "dotcloud_profile"), self._profile
        )

def get_service_class(svc_type):
    """Return the right “builder” class for the given service type or None."""

    return {
        "python-worker": PythonWorker,
        "custom": Custom
    }.get(svc_type)

def get_service(build_dir, svc_dir, svc_definition):
    """Return the right “builder” object for the given service.

    :param build_dir: directory where the source code has been untared.
    :param svc_dir: directory where the code for the current service is
                    (usually ~/current which points to build_dir + approot).
    :param svc_definition: the definition of the current service (the
                           dictionnary for the current service from
                           dotcloud.yml).
    :raises: ValueError, if no builder exists for this type of service.
    """

    service_class = get_service_class(svc_definition['type'])
    if not service_class:
        raise ValueError("No builder defined for {0} services".format(
            svc_definition['type']
        ))
    return service_class(build_dir, svc_dir, svc_definition)
