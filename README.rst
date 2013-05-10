dotCloud Sandbox
================

As `announced`__, dotCloud Sandbox is an open-source project which tries to
replicate the sandbox flavor of dotCloud: a free and easy way to build web
applications.

__ http://blog.dotcloud.com/new-sandbox

How does it work?
-----------------

Sandbox takes your application and its `dotcloud.yml`__ as input and outputs a
Docker_ image for each service that can be built; it doesn't support databases
(yet?).

__ http://docs.dotcloud.com/guides/build-file/

Sandbox tries to mimic the original dotCloud build process but a few
differences exist:

- database credentials won't be generated in environment.json_;
- postinstall_ is not executed (databases are supposed to be available when
  it's run), but you can probably use a post-build hook instead.

.. _Docker: https://github.com/dotcloud/docker
.. _environment.json: http://docs.dotcloud.com/guides/environment/
.. _postinstall: http://docs.dotcloud.com/guides/hooks/#post-install

Requirements
------------

- Docker (This is developed against master, but pretty much any release done
  after April 2013 should work);
- Python 2.7 (older versions *won't* work);
- A C compiler and the Python development headers.

.. vim: set tw=80 spelllang=en spell:
