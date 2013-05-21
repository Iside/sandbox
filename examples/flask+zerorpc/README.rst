Flask, ZeroRPC on Sandbox with Redis on dotCloud
================================================

This small example shows how to use the Sandbox to develop a dotCloud
application locally (while using a distant Redis database). To run it you will
need to `install Sandbox`_.

This application works directly on dotCloud too.

.. _install Sandbox: http://sandbox.dotcloud.com/user/installation.html

Deploy it on Sandbox
--------------------

First we need to set-up a development Redis server, you can deploy it wherever
you like, but if you have a dotCloud account, we can deploy a small Redis on the
Live flavor. That's what the script ``provision-redis.sh`` does::

    ./provision-redis.sh myappdevdb

“myappdevdb” is just an application name. Then, we can pull a base image for the
build::

    docker pull lopter/sandbox-base

Finally, build and run the application in Docker::

    sandbox build -i lopter/sandbox-base -e DOTCLOUD_DB_REDIS_URL="redis://user:pass@example.com:1234"
    sandbox run

Deploy it on dotCloud
---------------------

::

    dotcloud create myapp
    dotcloud push

Try it
------

Once the application is pushed you can queue/dequeue arbitrary JSON-serializable
objects via ZeroRPC::

    zerorpc tcp://<dotcloud-docker>:<zeroservice port> enqueue foo
    zerorpc tcp://<dotcloud-docker>:<zeroservice port> enqueue bar
    zerorpc tcp://<dotcloud-docker>:<zeroservice port> dequeue

And you check out the items in the queue::

    curl http://<dotcloud-docker>:<www port>

Here is a screencast_ of what it looks like!

.. _screencast: http://ascii.io/a/3230

.. vim: set tw=80 spelllang=en spell:
