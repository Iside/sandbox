# -*- coding: utf-8 -*-

import collections
import contextlib
import gevent
import gevent.subprocess
import logging
import re

from .exceptions import UnkownImageError, DockerCommandError, DockerNotFoundError
from .utils import bytes_to_human

class _CatchDockerError(object):
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is gevent.subprocess.CalledProcessError:
            if exc_value.returncode == 127:
                raise DockerNotFoundError()
            raise DockerCommandError(exc_value.output)
        return False

class Container(object):
    """Containers are transitions between two images.
    
    :param revpsec: the :class:`ImageRevSpec` of the image to use.
    :param commit_as: When :method:`run` is called, commit the resulting image
                      as this given :class:`ImageRevSpec`.
    :attr image: the image that will be used to start the container.
    :attr result: the revspec of the image commited when run finishes.
    :attr logs: the logs from the container when run finishes.

    .. note::

    :attr:`logs` and attr:`result` are only available once the :method:`run`
    has successfully finished.
    """

    PIPE = gevent.subprocess.PIPE
    STDOUT = gevent.subprocess.STDOUT

    def __init__(self, image, commit_as=None):
        self.image = image
        self.result = None
        self.logs = None
        self.commit_as = commit_as
        self._id = None

    def install_system_packages(self, packages):
        # XXX: pay attention to the tricks done in snapshots/worker.py
        pass

    @contextlib.contextmanager
    def run(self, cmd, stdin=None, stdout=None, stderr=None):
        """Run the specified command in a new container.

        This is a context manager that returns a :class:`subprocess.Popen`
        instance. When the context manager exit a new image is commited from
        the container and the container is automatically destroyed.

        The new image can be accessed via the :attr:`result` attribute.

        :param cmd: the program to run as a list of arguments.
        :param stdout, stderr: as in :class:`subprocess.Popen` except that you
                               should use Container.PIPE and Container.STDOUT
                               instead of subprocess.PIPE and subprocess.STDOUT.
        :param stdin: either None (close stdin) or Container.PIPE.
        :return: Nothing (this is a context manager) but sets :attr:`result`
                 with the class:`ImageRevSpec` of the resulting image.

        .. warning::

        stdout and stderr currently don't work due to limitations on Docker:
        you can't get the id of container, in a race-condition free way, with
        stdout and stderr enabled on docker run. A workaround would be to start
        a shell in detached mode and then execute the command from docker
        attach, but docker attach doesn't exit correctly when the process exits
        (it hangs on stdin until you try to write something which trigger an
        EBADF in docker).
        """

        logging.debug("Starting {0} in a {1} container".format(
            cmd, self.image
        ))

        try:
            # If stdin is None, start the container in detached mode, this will
            # print the id on stdout, then we simply wait for the container to
            # stop. If stdin is not None, start the container in attached mode
            # without stdout and stderr. This will print the container id on
            # stdout so we can read it.
            if stdin is None:
                with _CatchDockerError():
                    self._id = gevent.subprocess.check_output(
                        ["docker", "run", "-d", self.image.revision] + cmd
                    ).strip()
                # docker wait prints the number of second we waited, ignore it:
                with open("/dev/null", "w") as ignore:
                    docker = gevent.subprocess.Popen(
                        ["docker", "wait", self._id], stdout=ignore
                    )
            else:
                docker = gevent.subprocess.Popen(
                    ["docker", "run", "-i", "-a", "stdin", self.image.revision] + cmd,
                    stdin=stdin,
                    stdout=self.PIPE
                )
                # readline instead of read is important here, the object behind
                # docker.stdout is actually a socket._fileobject (yes, the real
                # socket module from Python) and its read method returns when
                # its buffer (8192 bytes by default on Python 2.7) is full or
                # when EOF is reached, not when the underlying read system call
                # returns.
                self._id = docker.stdout.readline().strip()
            logging.debug("Started container {0} from {1}".format(
                self._id, self.image
            ))

            yield docker

            # Wait for the process to terminate (if the calling code didn't
            # already do it):
            logging.debug("Waiting for container {0} to terminate".format(
                self._id
            ))
            docker.wait()
            logging.debug("Container {0} stopped".format(self._id))

            # Since we can't get stdout/stderr in realtime for now (see the
            # docstring), let's get the logs instead.
            logs = gevent.subprocess.Popen(
                ["docker", "logs", self._id],
                stdout=self.PIPE,
                stderr=self.STDOUT
            )
            logs = gevent.spawn(logs.communicate)

            # Commit a new image from the container
            username = repository = tag = None
            commit = ["docker", "commit", self._id]
            if self.commit_as:
                username = self.commit_as.username
                repository = self.commit_as.repository
                tag = self.commit_as.tag
                if self.commit_as.fqrn:
                    commit.append(self.commit_as.fqrn)
                if tag:
                    commit.append(tag)
            elif self.image.fqrn:
                username = self.image.username
                repository = self.image.repository
                tag = self.image.tag
                commit.append(self.image.fqrn)
                if repository and tag == "latest":
                    commit.append("latest")
            with _CatchDockerError():
                revision = gevent.subprocess.check_output(
                    commit, stderr=self.STDOUT
                ).strip()
            self.result = Image(ImageRevSpec(username, repository, revision, tag))
            logging.debug("Container {0} started from {1} commited as image {2}".format(
                self._id, self.image, self.result
            ))

            logging.debug("Fetching logs from container {0}".format(self._id))
            logs.join()
            with _CatchDockerError():
                # if we raise here, self.logs will stay at None which is wanted
                self.logs = logs.get()[0]
            logging.debug("{0} of logs fetched from container {1}".format(
                bytes_to_human(len(self.logs)), self._id
            ))
        finally:
            if self._id:
                # Destroy the container
                logging.debug("Destroying container {0}".format(self._id))
                with _CatchDockerError():
                    gevent.subprocess.check_call(["docker", "rm", self._id])
                logging.debug("Container {0} destroyed".format(self._id))

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
        if self.tag:
            s += ":{0}".format(self.tag)
            if self.revision:
                s += " ({0})".format(self.revision)
        else:
            if s:
                s += ":"
            s += self.revision
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
            elif username_and_repo == "<none>":
                repository = None
            else:
                repository = username_and_repo

        return username, repository

    @property
    def fqrn(self):
        """"Fully Qualified Repository Name"
        
        :return: the string username/repository if both are set, repository if
                 the username is missing, or None if everything is missing.
        """

        if self.username and self.repository:
            return "{0}/{1}".format(self.username, self.repository)
        return self.repository

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
                        tag = None if parts[1] == "<none>" else parts[1]
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
        logging.debug("Looking for {0} in docker images".format(revspec))
        with _CatchDockerError():
            images = gevent.subprocess.check_output(
                ["docker", "images"], stderr=gevent.subprocess.STDOUT
            ).splitlines()[1:]
        docker_revspecs = []
        for line in images:
            try:
                docker_revspecs.append(ImageRevSpec.parse_from_docker(line))
            except ValueError as ex:
                logging.warning(str(ex))
        # check that the image exists in Docker, and if so save it (it will
        # have the revision, which might not be the case of the revspec
        # received in argument).
        for docker_revspec in docker_revspecs:
            if revspec == docker_revspec:
                self.revspec = docker_revspec
                return
        raise UnkownImageError(
            "The image {0} doesn't exist "
            "(maybe you need to pull it in Docker?)".format(revspec)
        )

    def __str__(self):
        return self.revspec.__str__()

    def __repr__(self):
        return "<{0}(revspec={1}) at {2:#x}>".format(
            self.__class__.__name__, repr(self.revspec), id(self)
        )

    def __getattr__(self, name):
        if name in ["username", "repository", "revision", "tag", "fqrn"]:
            return getattr(self.revspec, name)
        raise AttributeError("'{0}' object has no attribute '{1}'".format(
            self.__class__.__name__, name
        ))

    def instantiate(self, *args, **kwargs):
        if self.revspec:
            return Container(self, *args, **kwargs)
        raise UnkownImageError(
            "You tried to instantiate a container from a destroyed image"
        )

    def destroy(self):
        logging.debug("Destroying image {0} from Docker".format(self.revspec))
        with _CatchDockerError():
            gevent.subprocess.check_call([
                "docker", "rmi", self.revspec.revision
            ])
        self.revspec = None
