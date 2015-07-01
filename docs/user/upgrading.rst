.. _upgrading:

=========
Upgrading
=========

.. contents::
   :local:


Upgrading the database
======================

Changes between Palladium versions may require upgrading the model
database or similar.  These upgrades are handled automatically by the
``pld-upgrade`` script.  Before running the script, make sure you've
set the ``PALLADIUM_CONFIG`` environment variable, then simply run:

.. code-block:: bash

  pld-upgrade

In some rare situations, it may be necessary to run the upgrade steps
of specific versions only.  ``pld-upgrade`` supports passing
``--from`` and ``--to`` options for that purpose.  As an example, if
you only want to run the upgrade steps between version ``0.9`` and
``1.0``, this is how you'd invoke ``pld-upgrade``:

.. code-block:: bash

  pld-upgrade --from=0.9.1 --to=1.0

Upgrading the Database persister from version 0.9.1 to 1.0
----------------------------------------------------------

Users of :class:`palladium.persistence.Database` that are upgrading
from version 0.9.1 to a more recent version (e.g. 1.0) are required
to invoke pld-upgrade with an explicit ``--from`` version like so:

.. code-block:: bash

  pld-upgrade --from=0.9.1

Backward incompatibilities in code
==================================

The development team makes an effort to try and keep the API backward
compatibility, and only gradually deprecate old code where necessary.
However, some changes between major Palladium versions still introduce
backward incompatibilities and potentially require you to update your
Palladium plug-ins.

Breaking changes between 0.9.1. and 1.0
---------------------------------------

Backward incompatible changes between 0.9.1. and 1.0 are of concern
only to users who have implemented their own version of
:class:`palladium.server.PredictService`.

:meth:`palladium.server.PredictService.sample_from_request` has been
replaced by the very similar
:meth:`~palladium.server.PredictService.sample_from_data`.  The new
method now accepts a ``data`` argument instead of ``request``.
``data`` is the equivalent of the former ``request.args``.  Similarly,
:meth:`palladium.server.PredictService.params_from_request` has been
replaced by :meth:`~palladium.server.PredictService.params_from_data`.
The latter now also accepts ``data`` instead of ``request``, which
again is the equivalent of the former ``request.data``.
