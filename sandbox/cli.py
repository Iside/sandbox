# -*- coding: utf-8 -*-

import argparse
import logging

logging.basicConfig(level="DEBUG")

def main():
    parser = argparse.ArgumentParser(
        description="Build Docker images for the given dotCloud application"
    )
    parser.add_argument("application",
        help="Path to your application source directory (where your dotcloud.yml is)"
    )

    args = parser.parse_args()

    logging.debug("Building {0}".format(args.application))
