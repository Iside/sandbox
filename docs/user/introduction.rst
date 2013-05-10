Pre-requisites & Limitations
============================

Sandbox takes your dotCloud application and then do the same job as Bob_ on
dotCloud, but using Docker_, and outputs Docker images.

Sandbox only knows how to build and run “stateless” services. It doesn't know
how to run and orchestrate “stateful” services (MySQL, Redis, MongoDB…). So, you
won't find database credentials in the environment_ and postinstall_ is not
executed (but you can probably use a post-build hook instead).

Of course, you can always deploy databases separately; thankfully Docker makes
that pretty easy and you should checkout the `Docker Index`_. Your favorite
database may has been already packaged for Docker. Then you can inject the
credentials in the environment and/or reconfigure your application.

Sandbox depends on Docker and Python and this is all covered in the
:doc:`installation` guide.

.. _Bob: http://docs.dotcloud.com/firststeps/how-it-works/#the-builder
.. _Docker: https://github.com/dotcloud/docker
.. _environment: http://docs.dotcloud.com/guides/environment/
.. _postinstall: http://docs.dotcloud.com/guides/hooks/#post-install
.. _Docker Index: https://index.docker.io/

.. vim: set tw=80 spelllang=en spell:
