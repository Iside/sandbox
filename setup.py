#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import subprocess

from setuptools import setup

execfile("sandbox/version.py")

# To build a service we use a "builder". It's a regular Python application that
# we inject in the container where we are doing the build. The best way I found
# to inject the builder is via a sdist tarball. It means that we need to
# distribute this tarball with the "sandbox" tool, so we have to build it first
# then we can use the sdist tarball as a "package data", hence all the
# weirdness here. If you a better idea, let us know!

# Copy them so they actually get packaged (otherwise setuptools just stores a
# ../xy relative path that won't exist when we install the sdist)
shutil.copyfile("sandbox/version.py", "builder/version.py")
shutil.rmtree("builder/udotcloud", ignore_errors=True)
shutil.copytree("udotcloud", "builder/udotcloud")

subprocess.check_call(
    ["/usr/bin/env", "python", "setup.py", "sdist", "--formats=gztar"],
    cwd="builder"
)

# Cython is a dependency of gevent:
requirements = ["pyyaml", "colorama>=0.2.5,<0.3", "Cython>=0.19,<0.20", "gevent"]
test_requires = ["unittest2"]

setup(
    name="udotcloud.sandbox",
    version=__version__,
    description="Build your app as you used to do on the dotCloud sandbox plan",
    author="dotCloud Inc.",
    author_email="opensource@dotcloud.com",
    url="https://github.com/dotcloud/sandbox",
    packages=["udotcloud", "udotcloud.sandbox"],
    package_dir={"udotcloud": "udotcloud", "udotcloud.sandbox": "sandbox"},
    package_data={"udotcloud.sandbox": ["../builder/dist/*", "../builder/*.sh"]},
    namespace_packages=["udotcloud"],
    include_package_data=True,
    entry_points={'console_scripts': ['sandbox = udotcloud.sandbox.cli:main']},
    test_suite="tests.run_all",
    install_requires=requirements,
    dependency_links=["https://github.com/surfly/gevent/tarball/master#egg=gevent-1.0rc2"],
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
