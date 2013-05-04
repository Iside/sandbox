# -*- coding: utf-8 -*-

import argparse
import colorama
import logging
import sys

from .builder import Builder
from ..utils.debug import configure_logging

def main():
    colorama.init()

    parser = argparse.ArgumentParser(description=
"""Internal builder for udotcloud.sandbox

This binary knows how to build a single service, of any type, from its sources
(a directory with two tarballs: application.tar —containing the application's
code— and service.tar —containing the service process definitions and
environment—).

This binary is called internally by udotcloud.sandbox and shouldn't be called
manually."""
    )
    parser.add_argument("sources", default=".",
        help="Path to the sources directory"
    )

    args = parser.parse_args()

    configure_logging("-->")

    try:
        builder = Builder(args.sources)
        if builder.build():
            sys.exit(0)
    except Exception:
        logging.exception("Sorry, the following bug happened:")
    sys.exit(1)
