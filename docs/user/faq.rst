.. faq:

==========================
Frequently asked questions
==========================

.. contents::
   :local:

How do I contribute to Palladium?
=================================

Everyone is welcome to contribute to Palladium.  You can help us
to improve Palladium when you:

- Use Palladium and give us feedback or submit bug reports to GitHub.

- Improve existing code or documentation and send us a pull request on
  GitHub.

- Suggest a new feature, and possibly send a pull request for it.

In case you intend to improve or to add code to Palladium, we kindly ask you to:

- Include documentation and tests for new code.

- Ensure that all existing tests still run successfully.

- Ensure backward compatibility in the general case.


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
information as needed to your logging or monitoring solution. Every
time, one of the functions is called, the decorators in the decorator
lists will also be called and can thus be used to generate logging
messages as needed. Let us assume you have implemented the decorators
`my_app.log.predict`, `my_app.log.alive`, `my_app.log.fit`,
`my_app.log.update_model`, and `my_app.log.load_data`, you can add
them to your application by adding the following parts to the
configuration:

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

    'load_data_decorators': [
        'my_app.log.load_data',
        ],


.. _virtual-env:

How can I use Python 3 without messing up with my Python 2 projects?
====================================================================

If you currently use an older version of Python or even need this
older version for other projects, you should take a look at virtual
environments.

If you use the default Python version, you could use `virtualenv`:

#. Install Python 3 if not yet available
#. pip install virtualenv
#. mkdir <virtual_env_folder>
#. cd <virtual_env_folder>
#. virtualenv -p /usr/local/bin/python3 palladium
#. source <virtual_env_folder>/palladium/bin/activate

If you use Anaconda, you can use the conda environments which can be
created and activated as follows:

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
provided with your operating system's distribution. In case there are
problems during installation, we refer to the installation
instructions of these projects:

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
            '!': 'palladium.util.Partial',
            'func': 'sklearn.cross_validation.StratifiedKFold',
            'random_state': 0,
            },
        'verbose': 4,
        'n_jobs': -1,
        }

Can I use Bayesian optimization instead of grid search to tune my hyperparameters?
==================================================================================

The grid search configuration allows you to use a class other than
:class:`sklearn.grid_search.GridSearchCV` to do the hyperparameter
search.  Here's an example configuration that uses `scikit-optimize
<https://scikit-optimize.github.io/>`_ to search for hyperparameters
using Bayesian optimization, assuming an :class:`sklearn.svm.SVC`
classifier:

.. code-block:: python

    'grid_search': {
        '!': 'skopt.BayesSearchCV',
        'estimator': {'__copy__': 'model'},
        'n_iter': 16,
        'search_spaces': {
            'C': {
                '!': 'skopt.space.Real',
                'low': 1e-6, 'high': 1e+1, 'prior': 'log-uniform',
            },
            'degree': {
                '!': 'skopt.space.Integer',
                'low': 1, 'high': 20,
            },
        },
        'return_train_score': True,
        'refit': False,
        'verbose': 4,
    }

Can I use my cluster to run a hyperparameter search?
====================================================

Yes.  We support using `dask.distributed
<http://distributed.readthedocs.io>`_ for distributing jobs among many
computers.  To install the necessary packages, run ``pip install dask
distributed``.

Here's a piece of configuration that will use Dask workers to run the
grid search:

.. code-block:: python

{
    'grid_search': {
        '!': 'palladium.fit.with_parallel_backend',
        'estimator': {
            '!': 'sklearn.model_selection.GridSearchCV',
            'estimator': {'__copy__': 'model'},
            'param_grid': {'__copy__': 'grid_search.param_grid'},
            'scoring': {'__copy__': 'scoring'},
        },
        'backend': 'dask',
    },

    '_init_client': {
        '!': 'dask.distributed.Client',
        'address': '127.0.0.1:8786',
    },
}

For details on how to set up Dask workers and a scheduler, please
consult the `Dask docs <https://docs.dask.org>`_.  But here's how you
would start up a scheduler and three workers locally:

.. code-block:: bash

    $ dask-scheduler
    Scheduler started at 127.0.0.1:8786

    $ dask-worker 127.0.0.1:8786  # start each in a new terminal
    $ dask-worker 127.0.0.1:8786
    $ dask-worker 127.0.0.1:8786    

How can I use test Palladium components in a shell?
===================================================

If you want to interactively check components of your Palladium
configuration, you can access Palladium's components as follows:

.. code-block:: python

    from palladium.util import initialize_config

    config = initialize_config(__mode__='fit')
    model = config['model']  # get model
    X, y = config['dataset_loader_train']()  # load training data
    # ...

You can also load the configuration to an interactive shell and access
the components directly:

.. code-block:: python

    from code import InteractiveConsole
    from pprint import pformat

    from palladium.util import initialize_config

    if __name__ == "__main__":
	config = initialize_config(__mode__='fit')
	banner = 'Palladium config:\n{}'.format(pformat(config))
	InteractiveConsole(config).interact(banner=banner)


In the interactive console, loading data and fitting a model can be
done like this:

.. code-block:: python

    X, y = dataset_loader_train()
    model.fit(X, y)


.. note::

  Make sure, the ``PALLADIUM_CONFIG`` environment variable is pointing
  to a valid configuration file.


How can I access the active model in my code?
=============================================

If you want to access the currently used model, you have to retrieve
it via the ``process_store`` or you have to load it using the model
persister:

.. code-block:: python

    from palladium.util import process_store
    model = process_store.get('model')

    from palladium.util import get_config
    model = get_config()['model_persister'].read()

.. note::

   ``get_config()['model']`` might not return the current active model
   as the entries in the configuration are not updated after
   initialization.
