Internal APIs Documentation
===========================

Sandbox is split into two Python package: ``sandbox`` and ``builder``. And
everything live in the ``udotcloud`` name space.

The sandbox package contains the code that's actually run when you use the
sandbox command. And the builder package is actually injected and installed in
each build container by sandbox. Once installed, sandbox launches the builder
inside the build container.

Sandbox
-------

.. automodule:: udotcloud.sandbox.sources
   :members:

.. automodule:: udotcloud.sandbox.containers
   :members:

.. automodule:: udotcloud.sandbox.exceptions
   :members:

Builder
-------

.. automodule:: udotcloud.builder.builder
   :members:

.. automodule:: udotcloud.builder.services
   :members:

.. vim: set tw=80 spelllang=en spell:
