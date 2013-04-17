# -*- coding: utf-8 -*-

import collections
import gevent.subprocess
import re

from .exceptions import UnkownImageError, DockerCommandError, DockerNotFoundError

class Container(object):
    """Containers are transitions between two images."""

    def __init__(self, image):
        self.image = image
        self.result = None
        self._id = None
        self._cmd = None

    def install_system_packages(self, packages):
        # XXX: pay attention to the tricks done in snapshots/worker.py
        pass

    def run(self, command):
        pass

_ImageRevSpec = collections.namedtuple(
    "_ImageRevSpec", ["username", "repository", "revision", "tag"]
)
class ImageRevSpec(_ImageRevSpec):
    """Human representation of an image revision in Docker."""

    def __str__(self):
        s = ""
        if self.username:
            s += "{0}/".format(self.username)
        if self.repository:
            s += self.repository
        s += ":{0}".format(self.tag if self.tag else self.revision)
        return s

    # Compare tags or revisions as needed (This allows us to seamlessly resolve
    # a tag into a revision in Image.__init__):
    def __eq__(self, other):
        if self.username == other.username and \
            self.repository == other.repository:
                if not self.revision or not other.revision:
                    return self.tag == other.tag
                return self.revision == other.revision
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def _is_revision(rev):
        return re.match("^({0}{{12}}|{0}{{64}})$".format("[0-9a-fA-F]"), rev)

    @staticmethod
    def _parse_user_and_repo(username_and_repo):
        username = repository = None
        user_separator = username_and_repo.find("/")
        if user_separator != 0:
            if username_and_repo and user_separator != -1:
                username = username_and_repo[:user_separator]
                repository = username_and_repo[user_separator + 1:]
            else:
                repository = username_and_repo
        return username, repository

    @classmethod
    def parse(cls, revspec):
        username = repository = revision = tag = username_and_repo = None
        revspec_len = len(revspec)
        rev_separator = revspec.find(":")
        user_separator = revspec.find("/")

        if user_separator == revspec_len - 1:
            raise ValueError("Invalid image: {0} (missing repository)".format(
                revspec
            ))
        if rev_separator == revspec_len - 1:
            raise ValueError("Invalid image: {0} (missing revision)".format(
                revspec
            ))

        if rev_separator != -1:
            rev_or_tag = revspec[rev_separator + 1:]
            if cls._is_revision(rev_or_tag):
                revision = rev_or_tag
            else:
                tag = rev_or_tag
            if rev_separator > 0:
                username_and_repo = revspec[:rev_separator]
        elif not cls._is_revision(revspec):
            username_and_repo = revspec
            tag = "latest"
        else:
            revision = revspec
        if username_and_repo:
            username, repository = cls._parse_user_and_repo(username_and_repo)
            if username is None and repository is None:
                raise ValueError("Invalid image: {0} (missing username)".format(
                    revspec
                ))

        if tag and not username_and_repo:
            raise ValueError(
                "Invalid image: {0} (tag without repository)".format(revspec)
            )

        return cls(username, repository, revision, tag)

    @classmethod
    def parse_from_docker(cls, revspec):
        username = repository = revision = tag = None

        if revspec:
            parts = re.split("\s+", revspec, maxsplit=3)
            parts_len = len(parts)
            if not revspec[0].isspace(): # we have an username and/or repo
                username, repository = cls._parse_user_and_repo(parts[0])
                if parts_len >= 2:
                    if cls._is_revision(parts[1]):
                        revision = parts[1]
                    elif parts_len >= 2:
                        tag = parts[1]
                        revision = parts[2]
            elif parts_len > 1:
                revision = parts[1]

        if revision and cls._is_revision(revision):
            return cls(username, repository, revision, tag)

        raise ValueError(
            "Invalid image: {0} (can't find the revision)".format(revspec)
        )

class Image(object):
    """Represent an image in Docker. Can be used to start a :class:`Container`.

    :param revspec: :class:`ImageRevSpec` that identify a specific image version.
    :raise UnkownImageError: if the image is not know from the local Docker.
    """

    def __init__(self, revspec):
        # list the images in Docker
        try:
            images = gevent.subprocess.check_output(
                ["docker", "images"], stderr=gevent.subprocess.STDOUT
            ).splitlines()[1:]
        except gevent.subprocess.CalledProcessError as ex:
            if ex.returncode == 127:
                raise DockerNotFoundError()
            raise DockerCommandError(ex.output)
        images = [ImageRevSpec.parse_from_docker(line) for line in images]
        # check that the image exists in Docker
        if revspec in images:
            self.revspec = revspec
            return
        raise UnkownImageError(
            "The base image {0} doesn't exist "
            "(maybe you need to pull it in Docker?)".format(revspec)
        )

    def instantiate(self):
        return Container(self._name, self._revision)
