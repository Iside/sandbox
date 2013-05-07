# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import random
import string
import unittest

from udotcloud.sandbox.containers import ImageRevSpec, Image
from udotcloud.sandbox.exceptions import UnkownImageError

class ContainerTestCase(unittest.TestCase):

    @staticmethod
    def random_image_name():
        return "{0}:unittest".format("".join(
            random.choice(string.ascii_lowercase) for i in xrange(10)
        ))

    def setUp(self):
        try:
            self.image = Image(ImageRevSpec.parse("lopter/sandbox-base:latest"))
            self.result_revspec = ImageRevSpec.parse(self.random_image_name())
            self.container = self.image.instantiate(commit_as=self.result_revspec)
        except UnkownImageError as ex:
            return self.skipTest(str(ex))

    def tearDown(self):
        if self.container.result:
            self.container.result.destroy()

class TestContainers(ContainerTestCase):

    def test_container_run_no_stdin(self):
        with self.container.run(["pwd"]):
            pass
        self.assertEqual(self.container.logs, "/\r\n")
        self.assertEqual(self.container.result.revspec, self.result_revspec)

    def test_container_run_stdin(self):
        with self.container.run(["cat"], stdin=self.container.PIPE) as cat:
            cat.stdin.write("TRAVERSABLE ")
            cat.stdin.write("WORMHOLE")
            cat.stdin.write("!\n")
            cat.stdin.close() # EOF
        self.assertEqual(self.container.logs, "TRAVERSABLE WORMHOLE!\n")
        self.assertEqual(self.container.result.revspec, self.result_revspec)

    def test_container_as_user(self):
        with self.container.run(["/bin/ls", "/root"], as_user="nobody"):
            pass
        self.assertIn("Permission denied", self.container.logs)

    def test_container_run_env(self):
        with self.container.run(["/usr/bin/env"], env={"TOTO": "POUET"}):
            pass
        self.assertIn("TOTO=POUET", self.container.logs)

    def test_container_as_user_stdin(self):
        with self.container.run(["/bin/ls", "/root"], as_user="nobody", stdin=self.container.PIPE) as ls:
            ls.stdin.close()
        self.assertIn("Permission denied", self.container.logs)

    def test_image_tag(self):
        with self.container.run(["pwd"]):
            pass
        self.assertEqual(self.container.result.tag, "unittest")
        tagged = self.container.result.add_tag("foobar")
        self.assertTupleEqual(
            tagged.revspec[:-1], self.container.result.revspec[:-1]
        )
        self.assertEqual(tagged.tag, "foobar")

    def test_run_stream_logs(self):
        with self.container.run_stream_logs(
            ["/bin/sh", "-c", "sleep 1; echo tick"],
            output=self.container.PIPE
        ) as container:
            self.assertIsInstance(container.ports, dict)
            output = container.communicate()[0]
            self.assertIn("tick\n", output)

    def test_run_stream_logs_ports(self):
        with self.container.run_stream_logs(
            ["/bin/sh", "-c", "sleep 1; echo tick"],
            output=self.container.PIPE,
            ports=[22]
        ) as container:
            self.assertIsInstance(container.ports, dict)
            self.assertIn(22, container.ports)
            output = container.communicate()[0]
            self.assertIn("tick\n", output)

    def test_run_stream_logs_env(self):
        with self.container.run_stream_logs(
            ["/bin/sh", "-c", "sleep 1; env"],
            output=self.container.PIPE,
            env={"TOTO": "POUET"}
        ) as container:
            self.assertIsInstance(container.ports, dict)
            output = container.communicate()[0]
            self.assertIn("TOTO=POUET", output)
