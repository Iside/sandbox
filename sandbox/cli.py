# -*- coding: utf-8 -*-

import argparse
import logging
import re
import sys

from .sources import Application

logging.basicConfig(level="DEBUG")

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

def main():
    parser = argparse.ArgumentParser(
        description="Build Docker images for the given dotCloud application"
    )
    parser.add_argument("-e", "--env", action="append",
        help="Define an environment variable (in the form KEY=VALUE) during the build"
    )
    parser.add_argument("application",
        help="Path to your application source directory (where your dotcloud.yml is)"
    )

    args = parser.parse_args()

    env = parse_environment_variables(args.env) if args.env else {}

    logging.debug("Loading {0}".format(args.application))
    application = Application(args.application, env)
    logging.debug("Application's buildfile: {0}".format(application))
    logging.debug("Application's environment: {0}".format(
        application.environment
    ))
    application.build()
