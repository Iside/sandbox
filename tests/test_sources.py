# -*- coding: utf-8 -*-

import json
import os
import shutil
import tempfile
import unittest2
import yaml

from udotcloud.sandbox import Application

class TestApplication(unittest2.TestCase):

    def setUp(self):
        self.path = os.path.dirname(__file__)

    def test_load_simple_application(self):
        application = Application(os.path.join(self.path, "simple_python_app"), {})
        self.assertEqual(len(application.services), 1)
        self.assertEqual(application.services[0].name, "www")
        self.assertEqual(application.services[0].type, "python")

    def test_load_custom_packages_application(self):
        application = Application(os.path.join(self.path, "custom_app"), {})
        self.assertListEqual(application.services[0].systempackages, ["postgresql"])

class TestService(unittest2.TestCase):

    def setUp(self):
        self.path = os.path.dirname(__file__)
        self.tmpdir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_generate_supervisor_include(self):
        self.application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {})
        self.service = self.application.services[0]
        supervisor_include = self.service._generate_supervisor_include(self.tmpdir)
        self.assertTrue(os.path.exists(supervisor_include))
        with open(supervisor_include) as fp:
            supervisor_include = fp.read()
        self.assertEqual("""[program:api]
command=/bin/sh -lc "exec gunicorn -k gevent -b 0.0.0.0:$PORT_WWW -w 2 wsgi:application"
directory=/home/dotcloud/current
stdout_logfile=/var/log/supervisor/api.log
stderr_logfile=/var/log/supervisor/api_error.log

""", supervisor_include)

    def test_generate_supervisor_include_custom_app(self):
        self.application = Application(os.path.join(self.path, "custom_app"), {})
        self.service = self.application.services[0]
        supervisor_include = self.service._generate_supervisor_include(self.tmpdir)
        self.assertTrue(os.path.exists(supervisor_include))
        with open(supervisor_include) as fp:
            supervisor_include = fp.read()
        self.assertEqual("""[program:db]
command=/bin/sh -lc "exec ~/run"
directory=/home/dotcloud
stdout_logfile=/var/log/supervisor/db.log
stderr_logfile=/var/log/supervisor/db_error.log

""", supervisor_include)

    def test_generate_environment_files(self):
        self.application = Application(os.path.join(self.path, "custom_app"), {"API_KEY": "42"})
        self.service = self.application.services[0]
        env_json, env_yml, env_profile = self.service._generate_environment_files(self.tmpdir)
        with open(env_json) as fp_json, open(env_yml) as fp_yml, open(env_profile) as fp_profile:
            env_json = json.load(fp_json)
            env_yml = yaml.safe_load(fp_yml)
            env_profile = {}
            for line in fp_profile:
                self.assertTrue(line.startswith("export "))
                key, value = line[len("export "):-1].split("=") # strip export and \n
                env_profile[key] = value
        for env in [env_json, env_yml, env_profile]:
            self.assertEqual(env.get("API_KEY"), "42")
            self.assertEqual(env.get("API_ENDPOINT"), self.service.environment["API_ENDPOINT"])
            self.assertEqual(env.get("DOTCLOUD_PROJECT"), self.application.name)
            self.assertEqual(env.get("DOTCLOUD_SERVICE_NAME"), self.service.name)

    def test_generate_service_tarball(self):
        self.application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {})
        self.service = self.application.services[0]
        application_tarball = os.path.join(self.tmpdir, "application.tar")
        with open(application_tarball, "w") as fp:
            fp.write("Test Content 42\n")
        service_tarball = self.service._generate_service_tarball(self.tmpdir, application_tarball)
        self.assertTrue(os.path.exists(service_tarball.dest))
        with open(service_tarball.dest, "r") as fp:
            service_tarball = fp.read()
        self.assertIn("Test Content 42\n", service_tarball)
        self.assertIn("DOTCLOUD_SERVICE_NAME", service_tarball)
