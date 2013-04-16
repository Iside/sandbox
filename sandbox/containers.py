# -*- coding: utf-8 -*-

import collections
import re

class Container(object):

    def __init__(self, image_name, image_revision):
        self._image_name = image_name
        self._image_revision = image_revision

    def _execute():
        pass

    def install_system_packages(self, packages):
        # XXX: pay attention to the tricks done in snapshots/worker.py
        pass

    def commit(self, msg):
        return Image(self._image_name, "latest")

_ImageRevSpec = collections.namedtuple(
    "_ImageRevSpec", ["username", "repository", "revision", "tag"]
)
class ImageRevSpec(_ImageRevSpec):
    @classmethod
    def parse(cls, revspec):
        username = repository = revision = tag = username_and_repo = None
        hexchar = "[0-9a-fA-F]"
        is_revision = lambda s: re.match(
            "^({0}{{12}}|{0}{{64}})$".format(hexchar), s
        )
        revspec_len = len(revspec)
        rev_separator = revspec.find(":")
        user_separator = revspec.find("/")

        if user_separator == 0:
            raise ValueError(
                "Invalid image: {0} (missing username)".format(revspec)
            )
        if user_separator == revspec_len - 1:
            raise ValueError(
                "Invalid image: {0} (missing repository)".format(revspec)
            )
        if rev_separator == revspec_len - 1:
            raise ValueError(
                "Invalid image: {0} (missing revision)".format(revspec)
            )

        if rev_separator != -1:
            rev_or_tag = revspec[rev_separator + 1:]
            if is_revision(rev_or_tag):
                revision = rev_or_tag
            else:
                tag = rev_or_tag
            if rev_separator > 0:
                username_and_repo = revspec[:rev_separator]
        elif not is_revision(revspec):
            username_and_repo = revspec
            tag = "latest"
        else:
            revision = revspec
        if username_and_repo and user_separator != -1:
            username = username_and_repo[:user_separator]
            repository = username_and_repo[user_separator + 1:]
        else:
            repository = username_and_repo

        if tag and not username_and_repo:
            raise ValueError(
                "Invalid image: {0} (tag without user/repo)".format(revspec)
            )

        return cls(username, repository, revision, tag)

    def __str__(self):
        s = ""
        if self.username:
            s += "{0}/".format(self.username)
        if self.repository:
            s += self.repository
        s += ":{0}".format(self.tag if self.tag else self.revision)
        return s

class Image(object):

    def __init__(self, revspec):
        self.revspec = revspec

    def instantiate(self):
        return Container(self._name, self._revision)
