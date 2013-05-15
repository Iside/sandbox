# -*- coding: utf-8 -*-

import unittest

from udotcloud.builder.templates import TemplatesRepository

class TestTemplatesRepository(unittest.TestCase):

    def test_render(self):
        repository = TemplatesRepository()
        nginx_conf = repository.render(
            "python", "nginx.conf",
            svc_dir="/home/dotcloud/current",
            supervisor_dir="/home/dotcloud/current/supervisor"
        )
        self.assertIn("/home/dotcloud/current/", nginx_conf)
