# -*- coding: utf-8 -*-

import argparse
import colorama
import logging
import re
import string
import sys

from .containers import ImageRevSpec, Image
from .exceptions import UnkownImageError
from .debug import configure_logging, log_success
from .sources import Application

def parse_environment_variables(env_list):
    env_dict = {}
    shell_var_re = re.compile('^[a-zA-Z][a-zA-Z0-9_]*$')
    for var in env_list:
        try:
            key, value = var.split("=")
        except ValueError:
            logging.error(
                "Environment variables should be in the "
                "form KEY=VALUE (got {0})".format(var)
            )
            sys.exit(1)
        if not shell_var_re.match(key) or not shell_var_re.match(value):
            logging.error(
                "Invalid character in the environment variable: {0}".format(var)
            )
            sys.exit(1)
        env_dict[key] = value
    return env_dict

def cmd_build(args, application):
    try:
        base_image = Image(ImageRevSpec.parse(args.image)) if args.image else None
    except ValueError as ex:
        logging.error("Can't parse your image revision/name: {0}".format(ex))
        sys.exit(1)
    except UnkownImageError:
        logging.error("The image {0} doesn't exist".format(args.image))
        sys.exit(1)

    logging.debug("Starting build with base image: {0}".format(
        base_image.revspec if base_image else "default"
    ))
    result_images = application.build(base_image)
    if result_images:
        log_success("{0} successfully built:\n    - {1}".format(
            application.name,
            "\n    - ".join([
                "{0}: {1}".format(service, image)
                for service, image in result_images.iteritems()
            ])
        ))
        sys.exit(0)
    elif result_images is not None:
        logging.warning("No buildable service found in {0}".format(
            application.name
        ))

def cmd_run(args, application):
    sys.exit(0 if application.run() else 1)

def main():
    colorama.init()

    parser = argparse.ArgumentParser(
        description="""Build and run dotCloud applications locally using Docker.

Since Docker doesn't have orchestration features only stateless services will
be recognized (i.e: database won't be started, and their infos won't be
generated in the environment).
"""
    )
    parser.add_argument("-v", "--verbosity", dest="log_lvl", default="info",
        type=string.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level to use on stderr"
    )

    subparsers = parser.add_subparsers(dest="cmd")

    parser_build = subparsers.add_parser("build",
        help="build Docker images from the given dotCloud application (directory)"
    )
    parser_build.add_argument("-e", "--env", action="append",
        help="Define an environment variable (in the form KEY=VALUE) during the build"
    )
    parser_build.add_argument("-i", "--image",
        help="Specify which Docker image to use as a starting point to build services"
    )
    parser_build.add_argument("application",
        help="Path to your application source directory (where your dotcloud.yml is)"
    )

    parser_run = subparsers.add_parser("run",
        help="run the given dotCloud application, using images previously built "
            "with the build command (EXPERIMENTAL)"
    )
    parser_run.add_argument("application",
        help="Path to your application source directory (where your dotcloud.yml is)"
    )

    args = parser.parse_args()
    if getattr(args, "env", None):
        env = parse_environment_variables(args.env)
    else:
        env = {}

    configure_logging(args.log_lvl)

    try:
        logging.debug("Loading {0}".format(args.application))
        try:
            application = Application(args.application, env)
        except IOError as ex:
            logging.error("Couldn't load {0}: {1}".format(
                args.application, ex.strerror
            ))
            sys.exit(1)
        logging.debug("Application's buildfile: {0}".format(application))
        logging.debug("Application's environment: {0}".format(
            application.environment
        ))
        logging.info("{0} successfully loaded with {1} service(s): {2}".format(
            application.name,
            len(application.services),
            ", ".join([
                "{0} ({1})".format(s.name, s.type) for s in application.services
            ])
        ))

        if args.cmd == "build":
            cmd_build(args, application)
        elif args.cmd == "run":
            cmd_run(args, application)
    except Exception:
        logging.exception("Sorry, the following bug happened:")
    sys.exit(1)
