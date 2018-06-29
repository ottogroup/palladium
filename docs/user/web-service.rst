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
      },
      "process_metadata": {}
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

List
----

The */list* handler returns model and model persister data.  Here's
some example output:

.. code-block:: json

   {
       "models": [
           {"train_timestamp": "2018-04-09T13:08:11.933814", "version": 1},
           {"train_timestamp": "2018-04-09T13:11:05.336124", 'version': 2}
       ],
       "properties": {"active-model": "8", "db-version": "1.2"}
   }

Fit, Update Model Cache, and Activate
-------------------------------------

Palladium allows for periodic updates of the model by use of the
:class:`palladium.persistence.CachedUpdatePersister`.  For this to
work, the web service's model persister checks its model database
source periodically for new versions of the model.  Meanwhile, another
process runs ``pld-fit`` and saves a new model into the same model
database.  When ``pld-fit`` is done, the web services will load the
new model as part of the next periodic update.

The second option is to call the */fit* web service endpoint, which
will essentially run the equivalent of ``pld-fit``, but in the web
service's process.  This has a few drawbacks compared to the first
method:

- The fitting will run inside the same process as the web service.
  While the model is fitting, your web service will likely use
  considerably more memory and processing while the fitting is
  underway.

- In multi-server or multi-process environments, you must take care of
  updating existing model caches (e.g. when running
  :class:`~palladium.persistence.CachedUpdatePersister`) by hand.  This
  can be done by calling the */update-model-cache* endpoint for each
  server process.

An example request to trigger a fit looks like this (assuming that
you're running a server locally on port 5000):

  http://localhost:5000/fit?evaluate=false&persist_if_better_than=0.9

The request will return immediately, after spawning a thread to do the
actual fitting work.  The JSON response has the job's ID, which we'll
later require next to check the status of our job:

.. code-block:: json

  {"job_id": "1adf9b2d-0160-45f3-a81b-4d8e4edf2713"}

The */alive* endpoint returns information about all jobs inside of the
``service_metadata.jobs`` entry.  After submitting above job, we'll
find that calling */alive* returns something like this:

.. code-block:: json

  {
      "palladium_version": "0.6",
      // ...
      "process_metadata": {
          "jobs": {
              "1adf9b2d-0160-45f3-a81b-4d8e4edf2713": {
                  "func": "<fit function>",
                  "info": "<MyModel>",
                  "started": "2018-04-09 09:44:52.660732",
                  "status": "finished",
                  "thread": 139693771835136
              }
          }
      }
  }

The ``finished`` status indicates that the job was successfully
completed.  ``info`` contains a string representation of the
function's return value.

When using a cached persister, you may also want to run the
*/update-model-cache* endpoint, which runs another job asynchronously,
the same way that */fit* does, that is, by returning an id and
storing information about the job inside of ``process_metadata``.
*/update-model-cache* will update the cache of any caching model
persisters, such as
:class:`~palladium.persistence.CachedUpdatePersister`.

The */fit* and */update-model-cache* endpoints aren't registered by
default with the Flask app.  To register the two endpoints, you can
either call the Flask app's ``add_url_rules`` directly or use the
convenience function :func:`palladium.server.add_url_rule` instead
inside of your configuration file.  An example of registering the two
endpoints is this:

.. code-block:: python

    'flask_add_url_rules': [
        {
            '__factory__': 'palladium.server.add_url_rule',
            'rule': '/fit',
            'view_func': 'palladium.server.fit',
            'methods': ['POST'],
        },
        {
            '__factory__': 'palladium.server.add_url_rule',
            'rule': '/update-model-cache',
            'view_func': 'palladium.server.update_model_cache',
            'methods': ['POST'],
        },
    ],

Another endpoint that's not registered by default is */activate*,
which works just like its command line counterpart: it takes a model
version and activates it in the model persister such that the next
prediction will use the active model.  The handler can be found at
:func:`palladium.server.activate`.  It requires a request parameter
called ``model_version``.
