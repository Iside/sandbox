# -*- coding: utf-8 -*-

import contextlib
import errno
import signal

def bytes_to_human(value):
    bytes_to_human = (
        (1024**4, "T"),
        (1024**3, "G"),
        (1024**2, "M"),
        (1024, "K"),
        (1, "B")
    )
    for factor, suffix in bytes_to_human:
        if abs(value) >= factor:
            value /= factor
            break
    return str(int(value)) + suffix

@contextlib.contextmanager
def ignore_eexist():
    try:
        yield
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            raise

def strsignal(signum):
    return {
        num: name
        for name, num in signal.__dict__.iteritems() if name.startswith("SIG")
    }.get(signum)
