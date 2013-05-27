#!/usr/bin/env python
# -*- coding: utf-8 -*-

import errno
import os
import shutil
import subprocess

from setuptools import setup

execfile("sandbox/version.py")

# The builder package builds into a binary that we want to inject (from the
# sandbox package) into each service we build. The best way (I found) to inject
# and install it on each service is via a sdist tarball. It means that we need
# to distribute it with the sandbox package (as "package data") which is also
# built here. Hence all the weird logic here to embed ourselves as package data.

# Cython is a dependency of gevent:
requirements = [
    "pyyaml",
    "colorama>=0.2.5,<0.3",
    "Cython>=0.19,<0.20",
    "gevent",
    "Jinja2>=2.6,<2.7"
]

package_dir = {
    "udotcloud": "udotcloud",
    "udotcloud.sandbox": "sandbox",
    "udotcloud.builder": "builder",
    "udotcloud.utils": "utils"
}

sdist = "dist/udotcloud.sandbox.tar.gz"

def check_sdist_outdated():
    try:
        sdist_mtime = os.stat(sdist).st_mtime
    except OSError as ex:
        if ex.errno == errno.ENOENT:
            return True

    for package in package_dir.itervalues():
        for root, dirs, files in os.walk(package):
            for name in files:
                source = os.path.join(root, name)
                try:
                    if os.stat(source).st_mtime > sdist_mtime:
                        return True
                except OSError:
                    pass

    return False

if check_sdist_outdated():
    print "==> sdist is outdated, building it first so we can embed it"
    try:
        os.makedirs(os.path.dirname(sdist), 0755)
    except OSError:
        pass
    with open(sdist, 'w') as dummy:
        dummy.write("Dummy data file, so setup.py can through\n")
    subprocess.check_call(["/usr/bin/env", "python", "setup.py", "sdist"])
    # Looks like setuptools truncate the destination tarball before the "build"
    # so we have to move it, otherwise we will package an empty file:
    shutil.copyfile("dist/udotcloud.sandbox-{0}.tar.gz".format(__version__), sdist)

setup(
    name="udotcloud.sandbox",
    version=__version__,
    description="Build your app as you used to do on the dotCloud sandbox plan",
    author="dotCloud Inc.",
    author_email="opensource@dotcloud.com",
    url="https://github.com/dotcloud/sandbox",
    packages=package_dir.keys(),
    package_dir=package_dir,
    namespace_packages=["udotcloud"],
    package_data={
        "udotcloud.sandbox": [
            "../builder/bootstrap.sh", os.path.join("..", sdist)
        ],
        "udotcloud.builder": ["templates/*/*"]
    },
    include_package_data=True,
    entry_points={"console_scripts": ["sandbox = udotcloud.sandbox.cli:main"]},
    # We can't use an entry point for dotcloud-builder, because setuptools will
    # check for sandbox's dependencies which we don't want to install inside
    # containers (see builder/bootstrap.sh):
    scripts=["builder/dotcloud-builder"],
    install_requires=requirements,
    dependency_links=[
        "https://github.com/surfly/gevent/tarball/b3a9ff1faf44015c672892aee07d08c7f7b85dcb#egg=gevent-1.0rc2"
    ],
    test_suite="tests.run_all",
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
