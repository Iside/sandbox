#!/bin/sh

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

pip install $sandbox_sdist

rm -f $sandbox_sdist $0
