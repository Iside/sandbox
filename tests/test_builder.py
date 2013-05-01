# -*- coding: utf-8 -*-

import gevent.subprocess
import logging; logging.basicConfig(level="DEBUG")
import os
import shutil
import tempfile
import unittest

from distutils.spawn import find_executable

from udotcloud.sandbox import Application
from udotcloud.builder import Builder

class TestBuilderCase(unittest.TestCase):

    sources_path = "simple_gunicorn_gevent_app"
    service_name = "api"

    def setUp(self):
        self.builddir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")
        # Fake /home/dotcloud directory:
        self.installdir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")
        self.code_dir = os.path.join(self.installdir, "code")
        self.current_dir = os.path.join(self.installdir, "current")
        self.path = os.path.dirname(__file__)
        self.application = Application(
            os.path.join(self.path, self.sources_path), {}
        )
        self.service = None
        for service in self.application.services:
            if service.name == self.service_name:
                self.service = service
                break
        if self.service is None:
            self.fail("Service {0} isn't defined in {1}".format(
                self.service_name, self.sources_path
            ))
        app_files = self.application._generate_application_tarball(self.builddir)
        svc_tarball = self.service._generate_service_tarball(self.builddir, app_files)
        gevent.subprocess.check_call([
            "tar", "-xf", svc_tarball.dest, "-C", self.installdir
        ])
        self.builder = Builder(self.installdir)

    def tearDown(self):
        shutil.rmtree(self.builddir, ignore_errors=True)
        shutil.rmtree(self.installdir, ignore_errors=True)

class TestBuilderUnpack(TestBuilderCase):

    sources_path = "simple_gunicorn_gevent_app"
    service_name = "api"

    def test_builder_unpack(self):
        self.builder._unpack_sources()

        self.assertTrue(os.path.isdir(self.code_dir))
        self.assertTrue(os.path.islink(self.current_dir))
        self.assertTrue(os.path.exists(os.path.join(self.code_dir, "dotcloud.yml")))
        self.assertTrue(os.path.exists(os.path.join(self.current_dir, "dotcloud.yml")))
        self.assertFalse(os.path.exists(os.path.join(self.installdir, "application.tar")))

        self.assertTrue(os.path.exists(os.path.join(self.installdir, "supervisor.conf")))
        self.assertTrue(os.path.exists(os.path.join(self.installdir, "environment.json")))
        self.assertTrue(os.path.exists(os.path.join(self.installdir, "environment.yml")))
        self.assertFalse(os.path.exists(os.path.join(self.installdir, "service.tar")))
        self.assertFalse(os.path.exists(os.path.join(self.installdir, "definition.json")))

class TestBuilderPythonWorker(TestBuilderCase):

    sources_path = "simple_gunicorn_gevent_app"
    service_name = "api"

    def test_builder_build(self):
        if not find_executable("virtualenv"):
            self.skipTest(
                "You need to install python-virtualenv "
                "to run the Python services unit tests"
            )

        self.builder.build()

        self.assertTrue(os.path.exists(os.path.join(self.current_dir, "prebuild")))
        self.assertTrue(os.path.exists(os.path.join(self.current_dir, "postbuild")))

        virtualenv_bin = os.path.join(self.installdir, "env", "bin")
        installed_packages = gevent.subprocess.Popen(
            [os.path.join(virtualenv_bin, "pip"), "freeze"],
            stdout=gevent.subprocess.PIPE
        )
        python_version = gevent.subprocess.Popen(
            [os.path.join(virtualenv_bin, "python"), "-V"],
            stderr=gevent.subprocess.PIPE
        )
        installed_packages = installed_packages.communicate()[0]
        python_version = python_version.communicate()[1]
        self.assertRegexpMatches(python_version, "^Python 2.7")
        self.assertIn("gunicorn", installed_packages)
