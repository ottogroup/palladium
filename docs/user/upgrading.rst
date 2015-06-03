.. _upgrading:

=========
Upgrading
=========

.. contents::
   :local:


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
==========================================================

Users of :class:`palladium.persistence.Database` that are upgrading
from version 0.9.1 to a more recent version (maybe 1.0) are required
to invoke pld-upgrade with an explicit ``--from`` version like so:

.. code-block:: bash

  pld-upgrade --from=0.9.1
