Installation
============

Set-up Docker
-------------

If you don't have it yet, you need to install Docker. You can do that manually_
in your own virtual machine or follow the `vagrant guide`_ (recommended).

.. _manually: http://docs.docker.io/en/latest/installation/ubuntulinux/
.. _vagrant guide: http://docs.docker.io/en/latest/installation/vagrant/

If you installed Docker manually, start it::

    docker -d

Then you have two choices:

#. Use sandbox from your Docker VM;
#. Install Docker (to get the Docker client) and Sandbox on your host.

The first option is the *simplest*, but you'll have to check out your dotCloud
applications on your Docker VM. The second choice is more complicated but allows
you to use your “local” dotCloud applications. Containers will still be deployed
on the VM if you redirect your local tcp/4242 port to it, you can do so with::

    ssh -vNL 4242:localhost:4242 your-user@vm-ip-or-address

Set-up Sandbox
--------------

Sandbox also depends:

- Python 2.7 (other versions *won't* work);
- A C compiler and the Python development headers;
- Python pip;
- Optionally, The libyaml and its development headers.

And git to checkout the code.

On Debian/Ubuntu (Wheezy/LTS or later), installing the following packages should
do the trick::

    python-pip python-dev build-essential libyaml-dev git

If you installed Docker using Vagrant, then you can just ssh to your Docker VM
and run::

    apt-get update
    apt-get install -y python-pip python-dev build-essential libyaml-dev git

Checkout Sandbox and install it::

    git clone git://github.com/dotcloud/sandbox.git
    cd sandbox
    pip install . -U

Then you can start to :doc:`use sandbox <usage>`.

.. vim: set tw=80 spelllang=en spell:
