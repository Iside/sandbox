# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import unittest2

from udotcloud.sandbox.containers import ImageRevSpec, Image
from udotcloud.sandbox.exceptions import UnkownImageError

class TestContainers(unittest2.TestCase):

    def setUp(self):
        try:
            self.image = Image(ImageRevSpec.parse("lopter/raring-base:latest"))
        except UnkownImageError as ex:
            return self.skipTest(str(ex))

    def test_container_run(self):
        pass
