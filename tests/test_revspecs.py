# -*- coding: utf-8 -*-

import unittest2

from udotcloud.sandbox.containers import ImageRevSpec, _ImageRevSpec

class TestRevSpecs(unittest2.TestCase):

    revspecs = {
        "": None,
        ":": None,
        "/": None,
        "/:": None,
        ":/": None,
        ":1234": None,
        ":33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        "33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        ":71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625": _ImageRevSpec(None, None, "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625", None),
        "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625": _ImageRevSpec(None, None, "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625", None),
        "repo:1234": _ImageRevSpec(None, "repo", None, "1234"),
        "user/repo:1234": _ImageRevSpec("user", "repo", None, "1234"),
        "user/repo": _ImageRevSpec("user", "repo", None, "latest"),
        "repo:71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625": _ImageRevSpec(None, "repo", "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625", None),
        "user/repo:33b6d177c4bd": _ImageRevSpec("user", "repo", "33b6d177c4bd", None),
        "user/repo:latest": _ImageRevSpec("user", "repo", None, "latest"),
        "user/repo:latest/v1": _ImageRevSpec("user", "repo", None, "latest/v1"),
        "user/repo:latest:v1": _ImageRevSpec("user", "repo", None, "latest:v1"),
        "user/repo/toto": _ImageRevSpec("user", "repo/toto", None, "latest"),
        ":user/repo": None
    }

    def test_revspecs(self):
        for revspec, result in self.revspecs.iteritems():
            if result is None:
                with self.assertRaises(ValueError):
                    ImageRevSpec.parse(revspec)
            else:
                self.assertEqual(ImageRevSpec.parse(revspec), result)
