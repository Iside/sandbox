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

[ -d $install_dir ] || mkdir -p $install_dir

[ -d $env_dir ] || virtualenv --python=python2.7 $env_dir

. $env_dir/bin/activate

builder_sdist=`dirname $0`/udotcloud.builder.tar.gz

pip install $builder_sdist

rm -f $builder_sdist $0
