#!/bin/sh -e

install_dir=/var/lib/dotcloud
env_dir=$install_dir/builder
run_dir=`dirname $0`

die() {
    echo >&2 $*
    exit 1
}

if [ `id -u` != 0 ] ; then
    die "$0 installs stuff in $install_dir and must be run as root"
fi

if ! type virtualenv >/dev/null ; then
    die "$0 depends on python-virtualenv"
fi

if ! type python2.7 >/dev/null ; then
    die "$0 depends on python2.7"
fi

[ -d $install_dir ] || mkdir -p $install_dir

[ -d $env_dir ] || virtualenv --python=python2.7 $env_dir

. $env_dir/bin/activate

sandbox_sdist=`dirname $0`/udotcloud.sandbox.tar.gz

# As a side effect of #2 this now installs the dependencies of the sandbox
# tool which include gevent which takes a long time to compile. So, let's
# install the dependencies manually here; hopefully they wan't change often.
pip install --no-deps -U $sandbox_sdist
pip install 'colorama>=0.2.5,<0.3' 'jinja2>=2.6,<2.7'

rm -f $sandbox_sdist $0
