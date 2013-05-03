#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

requirements = ["pyyaml", "colorama"]
test_requires = ["unittest2"]

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
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Build Tools"
    ],
    zip_safe=False
)
