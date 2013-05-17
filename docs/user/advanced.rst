Advanced Usage
==============

Creating “Base Images”
----------------------

Since Sandbox uses Docker it's fairly easy to add new base images that you can
use to build your services. dotCloud base images are just Ubuntu images with
some fairly minor modifications.

You can fork `lopter/sandbox-base`_ and make your own modifications.

Or, if you wish to create a base image from scratch using your favorite
Debian-like distribution you can start from a ``debootstrap --variant=minbase``
and:

Setup a sane sources.list::

    cat > /etc/apt/sources.list << EOF
    deb http://archive.ubuntu.com/ubuntu raring main universe multiverse restricted
    deb-src http://archive.ubuntu.com/ubuntu raring main universe multiverse restricted
    deb http://security.ubuntu.com/ubuntu raring-security main universe multiverse restricted
    deb-src http://security.ubuntu.com/ubuntu raring-security main universe multiverse restricted
    EOF

.. note::

   This one is for Ubuntu 13.04, obviously use a relevant one for your
   distribution

Prevent daemons from being started on installation or upgrades::

    cat  > /usr/sbin/policy-rc.d << EOF
    #!/bin/sh

    exit 101
    EOF
    chmod +x /usr/sbin/policy-rc.d

Prevent APT from installing unwanted packages::

    cat > /etc/apt/apt.conf.d/25norecommends << EOF
    APT
    {
        Install-Recommends  "false";
        Install-Suggests    "false";
    };
    EOF

And then install the following packages should be a sane base for any kind of
service::

    apt-get update
    apt-get install -y \
        language-pack-en lsb-release wget curl supervisor python2.7-dev \
        libssl-dev build-essential libevent-dev libpq-dev libsqlite3-dev \
        libyaml-dev ruby-dev uuid-dev libmysqlclient-dev libpcre3-dev \
        python-virtualenv zlib1g-dev less openssh-server

Clean up APT related files::

    apt-get clean
    rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

Add a dotcloud user::

    adduser --disabled-password dotcloud

And finally, hook ``dotcloud_profile`` in ``.profile``::

    cat << 'EOF' >> ~dotcloud/.profile

    if [ -f "$HOME/dotcloud_profile" ]; then
        . "$HOME/dotcloud_profile"
    fi
    EOF

.. _lopter/sandbox-base: https://index.docker.io/u/lopter/sandbox-base/

.. vim: set tw=80 spelllang=en spell:
