.. commands:

=======
Scripts
=======

Palladium includes a number of command-line scripts, many of which you
may have already encountered in the :ref:`tutorial`.

.. contents::
   :local:

pld-fit: *train models*
=======================

.. autosimple:: palladium.fit.fit_cmd

.. seealso::

   - :ref:`tutorial-run`

pld-test: *test models*
=======================

.. autosimple:: palladium.eval.test_cmd

.. seealso::

   - :ref:`tutorial-run`

pld-devserver: *serve the web API*
==================================

.. autosimple:: palladium.server.devserver_cmd

.. seealso::

   - :ref:`tutorial-run`
   - :ref:`deployment`

pld-stream: *make predictions through stdin and stdout*
=======================================================

.. autosimple:: palladium.server.stream_cmd

pld-grid-search: *find optimal hyperparameters*
===============================================

.. autosimple:: palladium.fit.grid_search_cmd

.. seealso::

   - :ref:`tutorial-grid-search`

pld-list: *list available models*
=================================

.. autosimple:: palladium.eval.list_cmd

pld-admin: *administer available models*
========================================

.. autosimple:: palladium.fit.admin_cmd

pld-version: *display version number*
=====================================

.. autosimple:: palladium.util.version_cmd

pld-upgrade: *upgrade database*
===============================

.. autosimple:: palladium.util.upgrade_cmd

.. seealso::

   - :ref:`upgrading`
