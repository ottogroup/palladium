.. faq:

==========================
Frequently asked questions
==========================

.. contents::
   :local:

How do I configure where output is logged to?
=============================================

Some commands, such as ``pld-fit`` use Python's own `logging framework
<https://docs.python.org/3/library/logging.html>`_ to print out useful
information.  Thus, we can configure where messages with which level
are logged to.  So maybe you don't want to log to the console but to a
file, or you don't want to see debugging messages at all while using
Palladium in production.

You can configure logging to suit your taste by adding a ``'logging'``
entry to the configuration.  The contents of this entry are expected
to follow the `logging configuration dictionary schema
<https://docs.python.org/2/library/logging.config.html#dictionary-schema-details>`_.
An example for this dictionary-based logging configuration format is
`available here
<https://docs.python.org/3/howto/logging-cookbook.html#an-example-dictionary-based-configuration>`_.

How can I combine Palladium with my logging or monitoring solution?
===================================================================

Similar to adding authentication support, we suggest to use the
different pluggable decorator lists in order to send logging or
monitoring messages to the corresponding systems. You need to
implement decorators which wrap the different functions and then send
information as needed to your logging or monitoring
solution. Every time, one of the functions is called, the decorators in
the decorator lists will also be called and can thus be used to
generate logging messages as needed. Let us assume you have
implemented the decorators `my_app.log.predict`, `my_app.log.alive`,
`my_app.log.fit`, and `my_app.log.update_model`, you can add them to
your application by adding the following parts to the configuration:

.. code-block:: python

    'predict_decorators': [
        'my_app.log.predict',
        ],

    'alive_decorators': [
        'my_app.log.alive',
        ],

    'update_model_decorators': [
        'my_app.log.update_model',
        ],

    'fit_decorators': [
        'my_app.log.fit',
        ],

.. _virtual-env:

How can I use Python 3 without messing up with my Python 2 projects?
====================================================================

If you currently use an older version of Python or even need this older version for other projects, you should take a look at virtual environments.

If you use the default Python version, you could use `virtualenv`:

#. Install Python 3 if not yet available
#. pip install virtualenv
#. mkdir <virtual_env_folder>
#. cd <virtual_env_folder>
#. virtualenv -p /usr/local/bin/python3 palladium
#. source <virtual_env_folder>/palladium/bin/activate

If you use Anaconda, you can use the conda environments which can be created and activated as follows:

#. conda create -n palladium python=3 anaconda
#. source activate palladium

.. note::

  Palladium's installation documentation for Anaconda is already using a
  virtual environment including the requirements.txt.

After having successfully activated the virtual environment, this
should be indicated by ``(palladium)`` in front of your shell command
line. You can also check, if ``python --version`` points to the
correct version. Now you can start installing Palladium.

.. note::

  The environment has to be activated in
  each context you want to call Palladium scripts (e.g., in a shell). So if
  you run into problems finding the Palladium scripts or get errors
  regarding missing packages, it might be worth checking if you have
  activated the corresponding environment.

Where can I find information if there are problems installing numpy, scipy, or scikit-learn?
============================================================================================

In the general case, the installation should work without problems if
you are using Anaconda or have already installed these packages as
provided with your operating system's distribution. In case there are problems during installation, we refer to the installation instructions of these projects:

* `numpy / scipy <http://www.scipy.org/install.html>`_
* `scikit-learn <http://scikit-learn.org/stable/install.html>`_

How do I use a custom cross validation iterator in my grid search?
==================================================================

Here's an example of a grid search configuration that uses a
:class:`sklearn.cross_validation.StratifiedKFold` with a parameter
``random_state=0``.  Note that the required ``y`` parameter for
:class:`~sklearn.cross_validation.StratifiedKFold` is created and
passed at runtime.

.. code-block:: python

    'grid_search': {
        'param_grid': {
            'C': [0.1, 0.3, 1.0],
            },
        'cv': {
            '__factory__': 'palladium.util.Partial',
            'func': 'sklearn.cross_validation.StratifiedKFold',
            'random_state': 0,
            },
        'verbose': 4,
        'n_jobs': -1,
        }
