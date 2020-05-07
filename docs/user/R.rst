.. _r:

=========
R support
=========

.. contents::
   :local:

Palladium has support for using dataset loaders and models written
in R.  There's wrapper classes for
:class:`~palladium.interfaces.DatasetLoader` and
:class:`~palladium.interfaces.Model` that can execute R code to do the
actual work.

To use Palladium's R support, you'll have to install R and the Python
`rpy2 <https://pypi.python.org/pypi/rpy2>`_ package and `tzlocal
<https://pypi.python.org/pypi/rpy2>`_.

A classification example
========================

Two examples are available in the ``examples/R`` folder in the source
tree of Palladium.  The first example fits the `iris` dataset loaded
in R using the R ``randomForest`` (:download:`config-iris.py
<../../examples/R/config-iris.py>`, :download:`iris.R
<../../examples/R/iris.R>`, :download:`iris.data
<../../examples/iris/iris.data>`).

In this example, function ``dataset`` is responsible for loading the
dataset, while ``train.randomForest`` does the fitting:

.. literalinclude:: ../../examples/R/iris.R
   :language: R
   :linenos:

When configuring a dataset loader that is programmed in R, use the
:class:`palladium.R.DatasetLoader`.  Note how this points to the
``dataset`` function inside the ``iris.R`` script that we defined
above:

.. code-block:: python

  'dataset_loader_train': {
      '!': 'palladium.R.DatasetLoader',
      'scriptname': 'iris.R',
      'funcname': 'dataset',
      },

R classification models are configured very similarly, using
:class:`palladium.R.ClassificationModel`.  This time, we point to the
``train.randomForest`` function that we defined in our R script.

.. code-block:: python

  'model': {
      '!': 'palladium.R.ClassificationModel',
      'scriptname': 'iris.R',
      'funcname': 'train.randomForest',
      'encode_labels': True,
      },

The configuration options are the same as for
:class:`~palladium.R.DatasetLoader` except for the ``encode_labels`` option,
which when set to ``True`` says that we would like to use a
:class:`sklearn.preprocessing.LabelEncoder` class to be able to deal
with string target values.  Thus ``['Iris-setosa', 'Iris-versicolor',
'Iris-virginica']`` will be visible to the R model as ``[0, 1, 2]``.

It is okay to use a :class:`~palladium.interfaces.DatasetLoader` that
is programmed in Python together with an R model.  In fact, another
configuration example demonstrates how to do this with the Iris
dataset:

.. literalinclude:: ../../examples/R/config-iris-dataset-from-python.py
   :language: python
   :linenos:


A regression example that uses categorical variables
====================================================

Another R example exists that solves a regression problem and makes
use of factor variables or categorical variables.  The Palladium
configuration for this example is found in :download:`config-tooth.py
<../../examples/R/config-tooth.py>` and the corresponding R code is in
:download:`tooth.R <../../examples/R/tooth.R>`.

In R, loading the dataset is done by the ``dataset`` function:

.. literalinclude:: ../../examples/R/iris.R
   :language: R
   :linenos:

When dealing with regression problems, we use
:class:`palladium.R.RegressionModel` to point to the R implementation.
Here's how this would look like:

.. code-block:: python

  'model': {
      '!': 'palladium.R.RegressionModel',
      'scriptname': 'tooth.R',
      'funcname': 'train.randomForest',
      },

The dataset is configured just like in the Iris example for
classification above:

.. code-block:: python

    'dataset_loader_train': {
        '!': 'palladium.R.DatasetLoader',
        'scriptname': 'tooth.R',
        'funcname': 'dataset',
    },

When dealing with categorical variables or factor variables, such as
found in the ``ToothGrowth`` data frame in the ``supp`` column, we
also need to use another component, namely Palladium's
:class:`palladium.R.Rpy2Transform`.  This is a standard scikit-learn
transformer, and it deals with the preservation of factor variables as
the data frame is converted from Python to R.

Here's what the final configuration of the tooth model looks like,
including :class:`~palladium.R.Rpy2Transform` in a
:class:`~sklearn.pipeline.Pipeline`:

.. code-block:: python

    'model': {
        '!': 'sklearn.pipeline.Pipeline',
        'steps': [
            ['rpy2', {
                '!': 'palladium.R.Rpy2Transform',
            }],
            ['regressor', {
                '!': 'palladium.R.RegressionModel',
                'scriptname': 'tooth.R',
                'funcname': 'train.randomForest',
            }],
        ],
    },

.. note::

  You should use :class:`palladium.R.Rpy2Transform` also when your
  dataset is loaded from R.  The reason is that when we get requests
  from the Python API, or from the web service, we will still have to
  deal with incoming data in the form of numpy arrays or pandas data
  frames, which this transformer allows us to deal with.
