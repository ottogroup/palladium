.. _r:

=========
R support
=========

.. contents::
   :local:


Palladium has support for using :class:`~palladium.interfaces.DatasetLoader` and
:class:`~palladium.interfaces.Model` objects that are programmed in the R
programming language.

To use Palladium's R support, you'll have to install R and the Python `rpy2
<https://pypi.python.org/pypi/rpy2>`_ package.

An example is available in the ``examples/R`` folder in the source
tree of Palladium (:download:`config.py <../../examples/R/config.py>`,
:download:`iris.R <../../examples/R/iris.R>`, :download:`iris.data
<../../examples/iris/iris.data>`).  It contains an example of a very
simple dataset loader and model implemented in R:

.. literalinclude:: ../../examples/R/iris.R
   :language: R
   :linenos:

When configuring a dataset loader that is programmed in R, use the
:class:`palladium.R.DatasetLoader`.  An example:

.. code-block:: python

  'dataset_loader_train': {
      '__factory__': 'palladium.R.DatasetLoader',
      'scriptname': 'iris.R',
      'funcname': 'dataset',
      },

The ``scriptname`` points to the R script that contains the function
``dataset``.

R models are configured very similarly, using
:class:`palladium.R.ClassificationModel`:

.. code-block:: python

  'model': {
      '__factory__': 'palladium.R.ClassificationModel',
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

It is okay to use a :class:`~palladium.interfaces.DatasetLoader` that is
programmed in Python together with an R model.
