# -*- coding: utf-8 -*-

import gevent
import gevent.subprocess

# Previous experience (in Python 2.6.x) has shown that the tarfile module is
# utterly broken, this is why tar is directly used here.

class TarError(Exception):
    pass

class TarCreateError(TarError):
    def __init__(self, returncode, stderr):
        self.message = "tar returned {0}: {1}".format(returncode, stderr)

class Tarball(object):
    """Utility class around :mod:`gevent.subprocess` and the tar command."""

    def __init__(self, dest, tar_process=None):
        self.dest = dest
        self._tar_process = tar_process
        self._stderr = gevent.spawn(tar_process.stderr.read)

    @classmethod
    def create_from_files(cls, files, dest, root_dir=None):
        # The companion method would be extract_from_stream but we don't need
        # it (we are going to use tar directly inside the container).
        cmd = ["tar", "-cf"]
        if isinstance(dest, basestring):
            cmd.append(dest)
            stdout = None
        else:
            cmd.append("-")
            stdout = dest
        if root_dir:
            cmd.extend(["-C", root_dir])
        cmd.extend(files if isinstance(files, list) else [files])

        tar = gevent.subprocess.Popen(
            cmd, stdout=stdout, stderr=gevent.subprocess.PIPE
        )
        return cls(dest, tar)

    def poll(self):
        """Poll the status of the tarball creation.

        :return: True if the tarball has been completely written else False.
        :raise TarCreateError: if tar didn't return 0.
        """

        return False if self.wait(_block=False) is False else True

    def wait(self, _block=True):
        """Wait until the tarball has been entirely written.

        :raise TarCreateError: if tar didn't return 0.
        """

        if _block:
            ret = self._tar_process.wait()
        else:
            ret = self._tar_process.poll()
            if ret is None:
                return False
        stderr = self._stderr.get()
        # as in communicate:
        self._tar_process.stderr.close()
        if self._tar_process.stdout:
            self._tar_process.stdout.close()
        if ret != 0:
            raise TarCreateError(ret, stderr)
