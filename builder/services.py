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

from .templates import TemplatesRepository
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
        self._sshd_config = os.path.join(self._supervisor_dir, "sshd_config")
        self._templates = TemplatesRepository()

    def _configure(self): pass
    def _install_requirements(self): pass

    def _run_hook(self, hook_script):
        hook_cmd = "chmod +x {0} >/dev/null 2>&1; exec {0}".format(hook_script)
        subprocess.check_call([ "/bin/sh", "-lc", hook_cmd], cwd=self._svc_dir)

    def _hook_prebuild(self):
        if self._prebuild_script:
            logging.info("Running prebuild hook `{0}`".format(self._prebuild_script))
            self._run_hook(self._prebuild_script)

    def _hook_postbuild(self):
        if self._postbuild_script:
            logging.info("Running postbuild hook `{0}`".format(self._postbuild_script))
            self._run_hook(self._postbuild_script)

    def _symlink_current(self):
        approot_dir = os.path.join(
            self._build_dir, "code", self._definition['approot']
        )
        # XXX
        logging.debug("Symlinking {1} from {0}".format(approot_dir, self._svc_dir))
        with ignore_eexist():
            os.symlink(approot_dir, self._svc_dir)

    def _configure_sshd(self):
        with open(self._sshd_config, "w") as fp:
            fp.write(self._templates.render(
                "common", "sshd_config", supervisor_dir=self._supervisor_dir
            ))
        cmds = []
        for algorithm in ["rsa", "dsa", "ecdsa"]:
            keypath = os.path.join(
                self._supervisor_dir, "ssh_host_{0}_key".format(algorithm)
            )
            if not os.path.exists(keypath):
                cmds.append([
                    "ssh-keygen", "-t", algorithm, "-N", "", "-f", keypath
                ])
        logging.info("Generating SSH host keys")
        subprocesses = [subprocess.Popen(cmd) for cmd in cmds]
        for process, cmd in zip(subprocesses, cmds):
            returncode = process.wait()
            if returncode:
                raise subprocess.CalledProcessError(returncode, cmd)

    def _generate_supervisor_configuration(self):
        # The configuration itself will be in ~dotcloud but put all the other
        # supervisor related files in a subdir:
        with ignore_eexist():
            os.mkdir(self._supervisor_dir)
        supervisord_conf = self._templates.render(
            "common", "supervisor.conf", supervisor_dir=self._supervisor_dir
        )
        with open(self._supervisor_include, 'w') as fp:
            fp.write(supervisord_conf)

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
            self._configure_sshd()
            self._configure()
            self._install_requirements()
            self._hook_postbuild()
        except subprocess.CalledProcessError as ex:
            cmd = " ".join(ex.cmd) if isinstance(ex.cmd, list) else ex.cmd
            msg = "Can't build service {0} ({1}): the command " \
                "`{2}` ".format(self._name, self._type, cmd)
            if ex.returncode < 0:
                signum = -ex.returncode
                logging.error(msg + "exited on signal {0} ({1})".format(
                    signum, strsignal(signum)
                ))
            elif ex.returncode == 127:
                logging.error(msg + "was not found")
            else:
                logging.error(msg + "returned {0}".format(ex.returncode))
            return ex.returncode
        return 0

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

    UWSGI_VERSION = ">=1.9.10,<1.10"

    def __init__(self, *args, **kwargs):
        PythonWorker.__init__(self, *args, **kwargs)
        self._nginx_conf = os.path.join(self._supervisor_dir, "nginx.conf")

    def _configure(self):
        PythonWorker._configure(self)
        logging.debug("Adding Nginx configuration")
        nginx_conf = self._templates.render(
            "python", "nginx.conf",
            supervisor_dir=self._supervisor_dir,
            svc_dir=self._svc_dir
        )
        with open(self._nginx_conf, "w") as fp:
            fp.write(nginx_conf)
        logging.debug("Adding Nginx and uWSGI to Supervisor")
        uwsgi_inc = self._templates.render(
            "python", "uwsgi.inc",
            supervisor_dir=self._supervisor_dir,
            virtualenv_dir=self._virtualenv_dir,
            exec_dir=self._svc_dir,
            config=self._definition['config']
        )
        nginx_inc = self._templates.render(
            "python", "nginx.inc",
            supervisor_dir=self._supervisor_dir
        )
        with open(self._supervisor_include, "a") as fp:
            fp.write(uwsgi_inc)
            fp.write(nginx_inc)
        logging.debug("Installing uWSGI {0}".format(self.UWSGI_VERSION))
        subprocess.check_call([
            self._pip, "install", "uWSGI {0}".format(self.UWSGI_VERSION)
        ])

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
        self._sshd_config = os.path.join(self._supervisor_dir, "sshd_config")
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
        "custom": Custom,
        "python": Python,
        "python-worker": PythonWorker
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
