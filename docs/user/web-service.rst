.. _web-service:

Web service
===========

Palladium includes an HTTP service that can be used to make predictions over
the web using models that were trained with the framework.  There are
two endpoints: */predict*, that makes predictions, and */alive* which
provides a simple health status.

.. contents::
   :local:

Predict
-------

The */predict* service uses HTTP query parameters to accept input
features, and outputs a JSON response.  The number and types of
parameters depend on the application.  An example is provided as part
of the :ref:`tutorial`.

On success, */predict* will always return an HTTP status of 200.  An
error is indicated by either status 400 or 500, depending on whether
the error was caused by malformed user input, or by an error on the
server.

The :class:`~palladium.interfaces.PredictService` must be configured to
define what parameters and types are expected.  Here is an example
configuration from the :ref:`tutorial`:

.. code-block:: python

    'predict_service': {
        '__factory__': 'palladium.server.PredictService',
        'mapping': [
            ('sepal length', 'float'),
            ('sepal width', 'float'),
            ('petal length', 'float'),
            ('petal width', 'float'),
            ],
        },

An example request might then look like this (assuming that you're
running a server locally on port 5000):

  http://localhost:5000/predict?sepal%20length=6.3&sepal%20width=2.5&petal%20length=4.9&petal%20width=1.5

The usual output for a successful prediction has both a ``result`` and
a ``metadata`` entry. The ``metadata`` provides the service name and
version as well as status information. An example:

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

An example that failed contains a ``status`` set to ``ERROR``, an
``error_code`` and an ``error_message``.  There is generally no
``result``.  Here is an example:

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

It's also possible to send a POST request instead of GET and predict
for a number of samples at the same time.  Say you want to predict for
the class for two Iris examples, then your POST body might look like
this:

.. code-block:: json

  [
    {"sepal length": 6.3, "sepal width": 2.5, "petal length": 4.9, "petal width": 1.5},
    {"sepal length": 5.3, "sepal width": 1.5, "petal length": 3.9, "petal width": 0.5}
  ]

The response will generally look the same, with the exception that now
there's a list of predictions that's returned:

.. code-block:: json

  {
      "result": ["Iris-virginica", "Iris-versicolor"],
      "metadata": {
          "service_name": "iris",
          "error_code": 0,
          "status": "OK",
          "service_version": "0.1"
          }
  }

Should a different output format be desired than the one implemented
by :class:`~palladium.interfaces.PredictService`, it is possible to use a
different class altogether by setting an appropriate ``__factory__``
(though that class will likely derive from
:class:`~palladium.interfaces.PredictService` for reasons of convenience).

A list of decorators may be configured such that they will be called
every time the */predict* web service is called.  To configure such a
decorator, that will act exactly as if it were used as a normal Python
decorator, use the ``predict_decorators`` list setting.  Here is an
example:

.. code-block:: python

    'predict_decorators': [
        'my_package.my_predict_decorator',
        ],

Alive
-----

The */alive* service implements a simple health check.  It'll provide
information such as the ``palladium_version`` in use, the current
``memory_usage`` by the web server process, and all metadata that has
been defined in the configuration under the ``service_metadata``
entry. Here is an example for the Iris service:

.. code-block:: json

  {
      "palladium_version": "0.6",
      "service_metadata": {
          "service_name": "iris",
	  "service_version": "0.1"
      },
      "memory_usage": 78,
      "model": {
          "updated": "2015-02-18T10:13:50.024478",
	  "metadata": {
	      "version": 2,
	      "train_timestamp": "2015-02-18T09:59:34.480063"
	  }
      }
  }

*/alive* can optionally check for the presence of data loaded into the
process' cache (``process_store``).  That is because some scenarios
require the model and/or additional data to be loaded in memory before
they can answer requests efficiently
(cf. :class:`palladium.persistence.CachedUpdatePersister` and
:class:`palladium.dataset.ScheduledDatasetLoader`).

Say you expect the ``process_store`` to be filled with a ``data``
entry (because maybe you're using
:class:`~palladium.dataset.ScheduledDatasetLoader`) before you're able to
answer requests.  And you want */alive* to return an error status (of
*503*) when that data hasn't been loaded yet, then you'd add to your
configuration the following entry:

.. code-block:: python

    'alive': {
        'process_store_required': ['data'],
        },
