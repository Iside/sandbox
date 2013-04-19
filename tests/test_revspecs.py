# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import unittest2

from udotcloud.sandbox.containers import ImageRevSpec, _ImageRevSpec

class TestRevSpecs(unittest2.TestCase):

    human_revspecs = {
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

    # As in the output of docker images
    docker_revspec = {
        "": None,
        "base" : None,
        # The space in front denotes the fac that an username/repo is missing
        # (the output of docker images is tabbed):
        " 33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        " 33b6d177c4bd just now": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        " latest 33b6d177c4bd just now": None,
        "base latest 33b6d177c4bd 3 weeks ago": _ImageRevSpec(None, "base", "33b6d177c4bd", "latest"),
        "<none> <none> 33b6d177c4bd 3 weeks ago": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        "<none> <none> 33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        "base latest 33b6d177c4bd": _ImageRevSpec(None, "base", "33b6d177c4bd", "latest"),
        "base 33b6d177c4bd": _ImageRevSpec(None, "base", "33b6d177c4bd", None),
        "base 33b6d177c4bd 3 weeks ago": _ImageRevSpec(None, "base", "33b6d177c4bd", None),
        "lopter/raring-base 33b6d177c4bd 3 weeks ago": _ImageRevSpec("lopter", "raring-base", "33b6d177c4bd", None),
        "lopter/raring-base latest 33b6d177c4bd 3 weeks ago": _ImageRevSpec("lopter", "raring-base", "33b6d177c4bd", "latest"),
    }

    def test_human_revspecs(self):
        for revspec, expected in self.human_revspecs.iteritems():
            if expected is None:
                with self.assertRaises(ValueError):
                    ImageRevSpec.parse(revspec)
            else:
                result = ImageRevSpec.parse(revspec)
                # We don't want to test ImageRevSpec.__eq__ here:
                self.assertEqual(result.username, expected.username)
                self.assertEqual(result.repository, expected.repository)
                self.assertEqual(result.revision, expected.revision)
                self.assertEqual(result.tag, expected.tag)

    def test_docker_revspecs(self):
        for revspec, expected in self.docker_revspec.iteritems():
            if expected is None:
                with self.assertRaises(ValueError):
                    ImageRevSpec.parse_from_docker(revspec)
            else:
                result = ImageRevSpec.parse_from_docker(revspec)
                self.assertEqual(result.username, expected.username)
                self.assertEqual(result.repository, expected.repository)
                self.assertEqual(result.revision, expected.revision)
                self.assertEqual(result.tag, expected.tag)
