# -*- coding: utf-8 -*-

class SandboxError(Exception):
    pass

class UnkownImageError(SandboxError):
    pass

class DockerError(Exception):
    pass

class DockerNotFoundError(Exception):
    pass

class DockerCommandError(Exception):
    pass
