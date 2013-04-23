#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

execfile("version.py")

setup(
    name="udotcloud.builder",
    version=__version__,
    description="Internal builder embedded by udotcloud.sandbox",
    author="dotCloud Inc.",
    author_email="opensource@dotcloud.com",
    url="https://github.com/dotcloud/sandbox",
    packages=["udotcloud", "udotcloud.builder"],
    package_dir={"udotcloud": "udotcloud", "udotcloud.builder": "."},
    namespace_packages=["udotcloud"],
    entry_points={'console_scripts': ['dotcloud-builder = udotcloud.builder.cli:main']},
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
