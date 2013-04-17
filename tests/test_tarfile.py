# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import gevent
import gevent.subprocess
import os
import shutil
import subprocess
import tempfile
import unittest2

from udotcloud.sandbox import tarfile

class TestTarballfile(unittest2.TestCase):

    def setUp(self):
        self.path = os.path.dirname(__file__)
        self.tmpdir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tar_simple_application(self):
        dest=os.path.join(self.tmpdir, "test.tar")
        tarball = tarfile.Tarball.create_from_files(
            "simple_python_app", dest=dest, root_dir=self.path
        )
        tarball.wait()
        self.assertEqual(dest, tarball.dest)
        self.assertTrue(os.path.exists(tarball.dest))

        with open("/dev/null", "w") as blackhole:
            ret = gevent.subprocess.call(
                ["tar", "-xf", tarball.dest, "-C", self.tmpdir],
                stdout=blackhole,
                stderr=subprocess.STDOUT
            )
        self.assertEqual(ret, 0)
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "simple_python_app", "dotcloud.yml"
        )))

    def test_tar_simple_application_to_fp(self):
        extract = gevent.subprocess.Popen(
            ["tar", "-xf", "-", "-C", self.tmpdir], stdin=subprocess.PIPE
        )
        tarball = tarfile.Tarball.create_from_files(
            "simple_python_app", dest=extract.stdin, root_dir=self.path
        )
        self.assertIsNotNone(tarball.dest)
        tarball.wait()
        self.assertEqual(extract.wait(), 0)

        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "simple_python_app", "dotcloud.yml"
        )))

    def test_tar_multiple_files(self):
        extract = gevent.subprocess.Popen(
            ["tar", "-xf", "-", "-C", self.tmpdir], stdin=subprocess.PIPE
        )
        tarball = tarfile.Tarball.create_from_files(
            ["simple_python_app", "custom_app"],
            dest=extract.stdin,
            root_dir=self.path
        )
        self.assertIsNotNone(tarball.dest)
        tarball.wait()
        self.assertEqual(extract.wait(), 0)

        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "simple_python_app", "dotcloud.yml"
        )))
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "custom_app", "dotcloud.yml"
        )))
