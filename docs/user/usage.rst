Using Sandbox
=============

Sandbox has two commands “build” and “run”. They both take the path to a
dotCloud application in parameter.

Build a dotCloud Application
----------------------------

To build an application you need a Docker image to start from. You can use
`lopter/sandbox-base`_ for that, which is based on Ubuntu 13.04 (Raring
Ringtail).

.. note::

   This image only supports the python and python-worker services with Python
   2.7 for now, but new images are easy to add.

.. note::

   Right now, Sandbox is still missing a mechanism to pick or override the base
   image for a specific type of service (so, the base image also has to support
   all the different type of services), but this will be added soon (see
   `#12`_).

.. _lopter/sandbox-base: https://index.docker.io/u/lopter/sandbox-base/
.. _#12: https://github.com/dotcloud/sandbox/issues/12

Then simply start the build::

    sandbox build -i lopter/sandbox-base path-to-your-dotcloud-app

At the end of the build, the images generated will be displayed.

.. note::

   Due to limitations in Docker the build logs cannot be streamed in real time,
   please be patient.

Run your Application
--------------------

.. warning:: Keep in mind that databases won't be started!

Use the run command and give it the path to your sources, Sandbox will lookup
the latest build of your sources and start Supervisor for each image::

    sandbox run path-to-your-dotcloud-app

This is it!

If you wish to extend Sandbox you can check out :doc:`advanced` and
:doc:`../developer/resources`.

.. vim: set tw=80 spelllang=en spell:
