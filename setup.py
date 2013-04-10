#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from setuptools import setup

requirements = ["pyyaml"]
test_requires = ["unittest2"]
if sys.version_info < (2, 7):
    requirements.append("argparse")

setup(
    name="udotcloud.sandbox",
    version="0.0.1",
    description="Build your app as you used to do on dotCloud's sandbox plan",
    author="dotCloud Inc.",
    author_email="opensource@dotcloud.com",
    url="https://github.com/dotcloud/sandbox",
    packages=["udotcloud", "udotcloud.sandbox"],
    package_dir={"udotcloud": "./udotcloud", "udotcloud.sandbox": "sandbox"},
    entry_points={'console_scripts': ['sandbox = udotcloud.sandbox.cli:main']},
    test_suite="tests.run_all",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Build Tools"
    ],
    zip_safe=False
)
