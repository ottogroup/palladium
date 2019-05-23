.. _configuration:

======================
Advanced configuration
======================

.. contents::
   :local:

Configuration is an important part of every machine learning project.
With Palladium, it is easy to separate code from configuration, and
run code with different configurations.

Configuration files use Python syntax.  For an introduction, please
visit the :ref:`tutorial`.

Palladium uses an environment variable called ``PALLADIUM_CONFIG`` to
look up the location of one or more configuration files.  If
``PALLADIUM_CONFIG`` is not set, Palladium will try to find a
configuration file at these locations:

- ``palladium-config.py``
- ``etc/palladium-config.py``

Variables
=========

Configuration files have access to environment variables, which allows
you to pass in things like database credentials from the environment:

.. code-block:: python

    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.SQL',
        'url': 'mysql://{}:{}@localhost/test?encoding=utf8'.format(
            environ['DB_USER'], environ['DB_PASS'],
            ),
        'sql': 'SELECT ...',
        }

You also have access to ``here``, which is the path to the directory
that the configuration file lives in.  In this example, we point the
``path`` variable to a file called ``data.csv`` inside of the same
folder as the configuration:

.. code-block:: python

    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.Table',
        'path': '{}/data.csv'.format(here),
        }

Multiple configuration files
============================

In larger projects, it's useful to split the configuration up into
multiple files.  Imagine you have a common ``config-data.py`` file and
several ``config-model-X.py`` type files, each of which use the same
data loader.  When using multiple files, you must separate the
filenames by commas:
``PALLADIUM_CONFIG=config-data.py,config-model-1.py``.

If your configuration files share some entries (keys), then files
coming later in the list will win and override entries from files
earlier in the list.  Thus, if the contents of ``config-data.py`` are
``{'a': 42, 'b': 6}``" and the contents of ``config-model-1.py`` is
``{'b': 7, 'c': 99}``, the resulting configuration will be ``{'a': 42,
'b': 7, 'c': 99}``.


Avoiding duplication in your configuration
==========================================

Even with multiple files, you'll sometimes end up repeating portions
of configuration between files.  The ``__copy__`` directive allows you
to copy or override existing entries.  Imagine your dataset loaders
for train and test are identical, except for the location of the CSV
file:

.. code-block:: python

    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.Table',
        'path': '{}/train.csv'.format(here),
        'many': '...',
        'more': {'...'},
        'entries': ['...'],
        }

    'dataset_loader_test': {
        '__factory__': 'palladium.dataset.Table',
        'path': '{}/test.csv'.format(here),
        'many': '...',
        'more': {'...'},
        'entries': ['...'],
        }

With ``__copy__``, you can reduce this down to:

.. code-block:: python

    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.Table',
        'path': '{}/train.csv'.format(here),
        'many': '...',
        'more': {'...'},
        'entries': ['...'],
        }

    'dataset_loader_test': {
        '__copy__': 'dataset_loader_train',
        'path': '{}/test.csv'.format(here),
        }

Reducing duplication in your configuration can help avoid errors.
