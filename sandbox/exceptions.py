# -*- coding: utf-8 -*-

"""
sandbox.exceptions
~~~~~~~~~~~~~~~~~~
"""

class SandboxError(Exception):
    """Base class for all exceptions in the `Sandbox`_ module."""
    pass

class UnkownImageError(SandboxError):
    """Raised when an Image cannot be found in Docker."""
    pass

class DockerError(Exception):
    pass

class DockerNotFoundError(DockerError):
    pass

class DockerCommandError(DockerError):
    pass
