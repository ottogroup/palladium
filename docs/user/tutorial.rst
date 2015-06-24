.. _tutorial:

========
Tutorial
========

.. contents::
   :local:


.. _tutorial-run:

Run the Iris example
====================

In this first part of the tutorial, we will run the simple Iris
example that is included in the source distribution of Palladium. The `Iris
data set <http://en.wikipedia.org/wiki/Iris_flower_data_set>`_
consists of a number of entries describing Iris flowers of three
different types and is often used as an introductory example for
machine learning.

It is assumed that you have already run through the
:ref:`installation`.  You can either download the files needed for the
tutorial here: :download:`config.py <../../examples/iris/config.py>`
and :download:`iris.data <../../examples/iris/iris.data>`.
Alternatively, you can find the files in the source tree of Palladium.
It should include the iris example in the ``examples/iris`` folder.
Navigate to that folder and list its contents:

.. code-block:: bash

  cd examples/iris
  ls

You will notice that there are two files here.  One is ``iris.data`` which
is a CSV file with the dataset we want to train with.  For each
training example, ``iris.data`` defines four features and one of the
three classes to predict.

The other file, ``config.py`` is our Palladium configuration file.  It has
all the configuration necessary to load the dataset CSV file and to
train it with a random forest classifier.

All the following commands require you to set an environment variable
to point to the ``config.py`` file.  In general, when using any of
Palladium's scripts, you will want to have that environment variable set and
pointing to your current project's ``config.py``.  Using Bash, you
could set the ``PALLADIUM_CONFIG`` environment variable so that it is picked
up by subsequent calls to Palladium like so:

.. code-block:: bash

  export PALLADIUM_CONFIG=config.py

Now we're all set to fit our Iris model:

.. code-block:: bash

  pld-fit

This command will print a number of lines and hopefully finish with
the message ``Wrote model with version 1``.  If you list the contents
of the directory you are in again, you will notice that there is a new
file called ``iris-model.db``.  This is the *SQLite database* that Palladium
created and saved our trained model in.  We can now use this trained
model and test it on a held-out test set:

.. code-block:: bash

  pld-test

This will output an accuracy score, which should be something around
96 percent.

If you run ``pld-fit`` again, you'll notice that it outputs ``Wrote
model with version 2``.  The next call to ``pld-test`` will use that
newer model to run tests.  To test the first model that you trained,
run:

.. code-block:: bash

  pld-test --model-version=1


.. _pld-devserver:

Let us try and use the web service that is included with Palladium to use our
trained model to generate predictions.  Run this command to bring up
the web server:

.. code-block:: bash

  pld-devserver

And now type this address into your browser's address bar (assuming
that you're running the server locally):

  http://localhost:5000/predict?sepal%20length=6.3&sepal%20width=2.5&petal%20length=4.9&petal%20width=1.5

The server should print out something like this:

.. code-block:: json

  {
      "result": "Iris-virginica",
      "metadata": {
          "service_name": "iris",
	  "error_code": 0,
	  "status": "OK",
	  "service_version": "0.1"
      }
  }

At this point we've already run through the palladium important scripts
that Palladium provides.


Understand Iris' config.py
==========================

In this section, we'll take a closer look at the Iris example's
``config.py`` file and how it wires together the components that we
use to train and predict on the Iris dataset.

Open up the ``config.py`` file inside the ``examples/iris`` directory
in Palladium's source folder and let us now walk step-by-step through the
entries of this file.

.. note::

  Despite the ``.py`` file ending, ``config.py`` is not conventional
  Python source code.  The file ending exists to help your editor to
  use Python syntax highlighting.  But all that ``config.py`` consists
  of is a single Python dictionary.


Dataset loaders
---------------

The first configuration entry we'll find inside ``config.py`` is
something called ``dataset_loader_train``.  This is where we configure
our dataset loader that helps us load the training data from the CSV
file with the data, and define which rows should be used as data and
target values.  The first entry inside ``dataset_loader_train``
defines the type of dataset loader we want to use.  That is
:class:`palladium.dataset.Table`:

.. code-block:: python

    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.Table',

The rest what is inside the ``dataset_loader_train`` are the keyword
arguments that are used to initialize the :class:`~palladium.dataset.Table`
component.  The full definition of ``dataset_loader_train`` looks like
this:

.. code-block:: python

    'dataset_loader_train': {
        '__factory__': 'palladium.dataset.Table',
        'path': 'iris.data',
        'names': [
            'sepal length',
            'sepal width',
            'petal length',
            'petal width',
            'species',
            ],
        'target_column': 'species',
        'sep': ',',
        'nrows': 100,
        }

You can now take a look at :class:`~palladium.dataset.Table`'s API to find
out what parameters a Table accepts and what they mean.  But to
summarize: the ``path`` is the path to the CSV file.  In our case,
this is the relative path to ``iris.data``.  Because our CSV file
doesn't have the column names in the first line, we have to provide
the column names using the ``names`` parameter.  The ``target_column``
defines which of the columns should be used as the value to be
predicted; this is the last column, which we named ``species``.  The
``nrows`` parameter tells :class:`~palladium.dataset.Table` to return only
the first hundred samples from our CSV file.

If you take a look at the next section in the config file, which is
``dataset_loader_test``, you will notice that it is very similar to
the first one.  In fact, the only difference between
``dataset_loader_train`` and ``dataset_loader_test`` is that the
latter uses a different subset of the samples available in the same
CSV file.  So instead of using ``nrows``, ``dataset_loader_test`` uses
the ``skiprows`` parameter and thus skips the first hundred examples
(in order to separate training and testing data):

.. code-block:: python

        'skiprows': 100,

Under the hood, :class:`~palladium.dataset.Table` uses
:func:`pandas.io.parsers.read_table` to do the actual loading.  Any
additional named parameters passed to :class:`~palladium.dataset.Table` are
passed on to :func:`~pandas.io.parsers.read_table`.  That is the case
for the ``sep`` parameter in our example, but there are a lot of other
useful options, too, like ``usecols``, ``skiprows`` and so on.

Palladium also includes a dataset loader for loading data from an SQL
database: :class:`palladium.dataset.SQL`.

But if you find yourself in need to write your own dataset loader,
then that is pretty easy to do: Take a look at Palladium's
:class:`~palladium.interfaces.DatasetLoader` interface that documents how a
:class:`~palladium.interfaces.DatasetLoader` like
:class:`~palladium.dataset.Table` needs to look like.


Model
-----

The next section in our Iris configuration example is ``model``.  Here
we define which machine learning algorithm we intend to use.  In our
case we'll be using a logistic regression classifier out of
scikit-learn:

.. code-block:: python

    'model': {
        '__factory__': 'sklearn.linear_model.LogisticRegression',
        'C': 0.3,
        },

Notice how we parametrize :class:`~sklearn.tree.LogisticRegression`
with the regularization parameter ``C`` set to ``0.3``.  To find out
which other parameters exist for the
:class:`~sklearn.linear_model.LogisticRegression` classifier, refer to
the `scikit-learn docs
<http://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html>`_.

If you've written your own scikit-learn estimator before, you'll
already know how to write your own :class:`palladium.interfaces.Model`
class.  You'll want to implement :meth:`~palladium.interfaces.Model.fit` for
model fitting, and :meth:`~palladium.interfaces.Model.predict` for
prediction of target values.  And possibly
:meth:`~palladium.interfaces.Model.predict_proba` if you're dealing with
class probabilities.

If you need to do pre-processing of your data, say scaling, value
imputation, feature selection, or the like, before you pass the data
into the ML algorithm (such as the
:class:`~sklearn.linear_model.LogisticRegression` classifier), you'll
want to take a look at `scikit-learn pipelines
<http://scikit-learn.org/stable/modules/pipeline.html>`_.  A Palladium
``model`` is not bound to be a simple estimator class; it can be a
composite of several pre-processing steps or `transformations
<http://scikit-learn.org/stable/data_transforms.html>`_, and the
algorithm combined.

At this point, feel free to change the configuration file to maybe try
out different values for *C*.  Can you find a setting for *C* that
produces better accuracy?


.. _tutorial-grid-search:

Grid search
-----------

Finding the right set of hyper parameters for your model can be
tedious.  That is where `grid search
<http://scikit-learn.org/stable/modules/grid_search.html>`_ comes in.
Using grid search, we can quickly try out a few parameters and use
cross-validation to see which of them work best.

Try running ``pld-grid-search`` and see what happens:

.. code-block:: bash

  pld-grid-search

At the end, you should see something like this output::

  [mean: 0.95000, std: 0.05138, params: {'C': 1.0},
   mean: 0.91000, std: 0.05022, params: {'C': 0.3},
   mean: 0.84000, std: 0.06408, params: {'C': 0.1}]

What happened?  We just tried out three different values for *C*,
and used a three-fold cross-validation to determine the best setting.
The first line is the winner.  It tells us that the mean
cross-validation accuracy of the model with *C* set to ``1.0`` is
``0.95`` and that the standard deviation between accuracies in the
cross-validation folds is ``0.05138``.

Let us take a look at the configuration of ``grid_search``:

.. code-block:: python

    'grid_search': {
        'param_grid': {
            'C': [0.1, 0.3, 1.0],
            },
        'verbose': 4,
        }

What parameters should be checked can be specified in the entry
``param_grid``. If more than one parameter with sets of values to
check are provided, all possible combinations are explored by grid
search. ``verbose`` allows to set the level for grid search
messages. It is possible to set other parameters of grid search, e.g.,
how many jobs to be run in parallel can be specified in `n_jobs` (if
set to -1, all cores are used).

Palladium uses :class:`sklearn.grid_search.GridSearchCV` to do the actual
work.  Thus, you'll want to take a look at the `scikit-learn docs for
grid search
<http://scikit-learn.org/stable/modules/generated/sklearn.grid_search.GridSearchCV.html>`_
to understand what these parameters mean and what other parameters
exist for ``grid_search``.


Model persister
---------------

Usually we'll want the ``pld-fit`` command to save the trained model
to disk.

The ``model_persister`` in the Iris ``config.py`` file is set up to
save those models into a SQLite database.  Let us take a look at that
part of the configuration:

.. code-block:: python

    'model_persister': {
        '__factory__': 'palladium.persistence.CachedUpdatePersister',
        'update_cache_rrule': {'freq': 'HOURLY'},
        'impl': {
            '__factory__': 'palladium.persistence.Database',
            'url': 'sqlite:///iris-model.db',
            },
        },

The :class:`palladium.persistence.CachedUpdatePersister` wraps the persister
actually responsible for reading and writing models. It is possible to
provide an update rule which specifies intervals to update the
model. In the configuration above, the `update_cache_rrule` is set to
an hourly update (in real applications, the frequency will palladium likely
be much lower like daily or weekly). For details how to define these
rules we refer to the `python-dateutil docs
<https://labix.org/python-dateutil>`_. If no `update_cache_rrule` is
provided, the model will not be updated automatically. The `impl`
entry of this model persister specifies the actual persister to be
wrapped.

The :class:`palladium.persistence.Database` persister takes a single
argument ``url`` which is the URL of the database to save the fitted
model into.  It will automatically create a table called ``models`` if
such a table doesn't exist yet.  Please refer to the `SQLAlchemy docs
<http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#database-urls>`_
for details on which databases are supported, and how to form the
database URL.

Palladium ships with another model persister called
:class:`palladium.persistence.File` that writes pickles to the file system.
If you want to store your model anywhere else, or if you do not use
Python's pickle but something else, you might want to take a look at the
:class:`~palladium.interfaces.ModelPersister` interface, which describes the
necessary methods. The location for storing the files can be chosen
freely. However, the path has to contain a placeholder for adding the
model's version:

.. code-block:: python

    'model_persister': {
        '__factory__': 'palladium.persistence.CachedUpdatePersister',
        'impl': {
            '__factory__': 'palladium.persistence.File',
            'path': 'model-{version}.pickle',
            },
        },



Predict service
---------------

The last component in the Iris example configuration is called
``predict_service``.  The :class:`palladium.interfaces.PredictService` is
the workhorse behind what us happening in the ``/predict`` HTTP
endpoint.  Let us take a look at how it is configured:

.. code-block:: python

    'predict_service': {
        '__factory__': 'palladium.server.PredictService',
        'mapping': [
            ('sepal length', 'float'),
            ('sepal width', 'float'),
            ('petal length', 'float'),
            ('petal width', 'float'),
            ],
        }

Again, the specific implementation of the ``predict_service`` that we
use is specified through the ``__factory__`` setting.

The ``mapping`` defines which request parameters are to be expected.
In this example, we expect a ``float`` number for each of ``sepal
length``, ``sepal width``, ``petal length``, ``petal width``.  Note
that this is exactly the order in which the data was fed into the
algorithm for model fitting.

An example request might then look like this (assuming that you're
running a server locally on port 5000):

  http://localhost:5000/predict?sepal%20length=6.3&sepal%20width=2.5&petal%20length=4.9&petal%20width=1.5

The :class:`palladium.server.PredictService` implementation that we use in
this example has some more settings.

Its responsibility is also to create an HTTP response.  In our
example, if the prediction was successful (i.e., no errors whatsoever
occurred), then the :class:`~palladium.server.PredictService` will generate a
JSON response with an HTTP status code of 200:

.. code-block:: json

  {
      "result": "Iris-virginica",
      "metadata": {
          "service_name": "iris",
	  "error_code": 0,
	  "status": "OK",
	  "service_version": "0.1"
      }
  }

In case of a malformed request, you will see a status code of 400 and
this response body:

.. code-block:: json

  {
      "metadata": {
          "service_name": "iris",
	  "error_message": "BadRequest: ...",
	  "error_code": -1,
	  "status": "ERROR",
	  "service_version": "0.1"
      }
  }

If you want the predict service to work differently, then chances are
that you get away subclassing from the
:class:`~palladium.server.PredictService` class and override one of its
methods.  E.g. to change the way that API responses to the web look
like, you would override the
:meth:`~palladium.server.PredictService.response_from_prediction` and
:meth:`~palladium.server.PredictService.response_from_exception` methods,
which are responsible for creating the JSON responses.


Implementing the model as a pipeline
------------------------------------

As mentioned in the `Model`_ section, it is entirely
possible to implement your own machine learning model and use it.
Remember that the only interface our model needed to implement was
:class:`palladium.interfaces.Model`.  That means we can also use a
`scikit-learn Pipeline
<http://scikit-learn.org/stable/modules/pipeline.html>`_ to do the
job.  Let us extend our Iris example to use a pipeline with two
elements: a :class:`sklearn.preprocessing.PolynomialFeatures`
transform and a :class:`sklearn.linear_model.LogisticRegression`
classifier.  To do this, let us create a file called ``iris.py`` in the
same folder as we have our ``config.py`` with the following contents:

.. code-block:: python

  from sklearn.linear_model import LogisticRegression
  from sklearn.pipeline import Pipeline
  from sklearn.preprocessing import PolynomialFeatures

  def model(**kwargs):
      pipeline = Pipeline([
          ('poly', PolynomialFeatures()),
          ('clf', LogisticRegression()),
          ])
      pipeline.set_params(**kwargs)
      return pipeline

The special ``**kwargs`` argument allows us to pass configuration
options for both the ``poly`` and the ``clf`` elements of our pipeline
in the configuration file.  Let us try this: we change the ``model``
entry in ``config.py`` to look like this:

.. code-block:: python

    'model': {
        '__factory__': 'iris.model',
        'clf__C': 0.3,
        },

Just like in our previous example, we are setting the ``C`` hyper
parameter of our :class:`~sklearn.linear_model.LogisticRegression` to
be ``0.3``.  However, this time, we have to prefix the parameter name
by ``clf__`` to tell the pipeline that we want to the set a parameter
of the ``clf`` part of the pipeline. If you want to used grid search
with this pipeline, keep in mind that you will also need to adapt the
parameter's name in the grid search section to `clf_C`.
