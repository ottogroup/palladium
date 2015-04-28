.. _installation:

============
Installation
============

Palladium requires Python 3.3 or better to run. If you are currently using
an older version of Python, you might want to check the :ref:`FAQ
entry about virtual environments <virtual-env>`.  Some of Palladium's
dependencies such as ``numpy``, ``scipy`` and ``scikit-learn`` may
require a C compiler to install.

All of Palladium's dependencies are listed in the ``requirements.txt`` file.
You can use either ``pip`` or ``conda`` to install the dependencies
from this file.

For most installations, it is recommended to install Palladium and its
dependencies inside a virtualenv or a conda environment.  The
following commands assume that you have your environment active.

Install from PyPI
=================

It is a good practice to install dependencies with exactly the same
version numbers that the release was made with.  You can find the
``requirements.txt`` that defines those version numbers in the top
level directory of Palladium's source tree or can download it here:
:download:`requirements.txt <../../requirements.txt>`.  You can
install the dependencies with the following command:

.. code-block:: bash

  pip install -r requirements.txt

In order to install Palladium from PyPI, simply run:

.. code-block:: bash

  pip install palladium

Install from binstar
====================

For installing Palladium with `conda install`, you have to add the
following binstar channel first:

.. code-block:: bash

  conda config --add channels https://conda.binstar.org/ottogroup
  conda install palladium

.. note::

  Right now, there are only versions for `linux-64` and `osx-64`
  platforms available at our binstar channel.

Install from source
===================

Download and navigate to your copy of the Palladium source, then run:

.. code-block:: bash

  cd palladium
  pip install -r requirements.txt

To install the Palladium package itself, run:

.. code-block:: bash

  python setup.py install  # or 'setup.py dev' if you intend to develop Palladium itself

If you prefer conda over using pip, run these commands instead to
install:

.. code-block:: bash

  cd palladium
  conda create -n palladium python=3 --file requirements.txt  #create conda environment
  source activate palladium  # activate conda environment
  python setup.py install

.. note::

  The `virtualenv` or `conda create` and `source activate` commands
  above generate and activate an environment where specific Python
  package versions can be installed for a project without interferring
  with other Python projects. This environment has to be activated in
  each context you want to call Palladium scripts (e.g., in a shell). So if
  you run into problems finding the Palladium scripts or get errors
  regarding missing packages, it might be worth checking if you have
  activated the corresponding environment. If you want to deactivate
  an environment, simply run `deactivate` (or `source deactivate` for
  conda environments).

.. note::

  If you intend to develop Palladium itself or if you want to run the
  tests, you additionally need to install the
  :download:`requirements-dev.txt <../../requirements-dev.txt>` with
  ``pip install -r requirements-dev.txt`` (or ``conda install --file
  requirements-dev.txt`` in the Anaconda setting).


Once you have Palladium installed, you should be able to use the
``pld-version`` command and find out which version of Palladium you're
using:

.. code-block:: bash

  pld-version

Now that you've successfully installed Palladium, it's time to head over to
the :ref:`tutorial` to learn about what it can do for you.
