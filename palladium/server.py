"""HTTP API implementation.
"""

import sys
from docopt import docopt
from flask import Flask
from flask import make_response
from flask import request
import numpy as np
import ujson
from werkzeug.exceptions import BadRequest

from . import __version__
from .interfaces import PredictError
from .util import args_from_config
from .util import get_config
from .util import get_metadata
from .util import initialize_config
from .util import logger
from .util import memory_usage_psutil
from .util import PluggableDecorator
from .util import process_store

app = Flask(__name__)


def make_ujson_response(obj, status_code=200):
    """Encodes the given *obj* to json and wraps it in a response.

    :return:
      A Flask response.
    """
    json_encoded = ujson.encode(obj, ensure_ascii=False, double_precision=-1)
    resp = make_response(json_encoded)
    resp.mimetype = 'application/json'
    resp.content_type = 'application/json; charset=utf-8'
    resp.status_code = status_code
    return resp


class PredictService:
    """A default :class:`palladium.interfaces.PredictService`
    implementation.

    Aims to work out of the box for the most standard use cases.
    Allows overriding of specific parts of its logic by using granular
    methods to compose the work.
    """
    types = {
        'float': float,
        'int': int,
        'str': str,
        'bool': lambda x: x.lower() == 'true',
        }

    def __init__(self, mapping, params=(), predict_proba=False, **kwargs):
        """
        :param mapping:
          A list of query parameters and their type that should be
          included in the request.  These will be processed in the
          :meth:`sample_from_data` method to construct a sample
          that can be used for prediction.  An example that expects
          two request parameters called ``pos`` and ``neg`` that are
          both of type str::

            { ...
              'mapping': [('pos', 'str'), ('neg', 'str')]
            ... }

        :param params:
          Similarly to *mapping*, this is a list of name and type of
          parameters that will be passed to the model's
          :meth:`~palladium.interfaces.Model.predict` method as keyword
          arguments.

        :param predict_proba:
          Instead of returning a single class (the default), when
          *predict_proba* is set to true, the result will instead
          contain a list of class probabilities.
        """
        self.mapping = mapping
        self.params = params
        self.predict_proba = predict_proba
        vars(self).update(kwargs)

    def __call__(self, model, request):
        try:
            return self.do(model, request)
        except Exception as e:
            return self.response_from_exception(e)

    def do(self, model, request):
        if request.method == 'GET':
            single = True
            samples = np.array([self.sample_from_data(model, request.args)])
        else:
            single = False
            samples = []

            for data in request.json:
                samples.append(self.sample_from_data(model, data))
            samples = np.array(samples)

        params = self.params_from_data(model, request.args)
        y_pred = self.predict(model, samples, **params)
        return self.response_from_prediction(y_pred, single=single)

    def sample_from_data(self, model, data):
        """Convert incoming sample *data* into a numpy array.

        :param model:
          The :class:`~Model` instance to use for making predictions.
        :param data:
          A dict-like with the sample's data, typically retrieved from
          ``request.args`` or similar.
        """
        values = []
        for key, type_name in self.mapping:
            value_type = self.types[type_name]
            values.append(value_type(data[key]))
        return np.array(values, dtype=object)

    def params_from_data(self, model, data):
        """Retrieve additional parameters (keyword arguments) for
        ``model.predict`` from request *data*.

        :param model:
          The :class:`~Model` instance to use for making predictions.
        :param data:
          A dict-like with the parameter data, typically retrieved
          from ``request.args`` or similar.
        """
        params = {}
        for key, type_name in self.params:
            value_type = self.types[type_name]
            if key in data:
                params[key] = value_type(data[key])
            elif hasattr(model, key):
                params[key] = getattr(model, key)
        return params

    def predict(self, model, sample, **kwargs):
        if self.predict_proba:
            return model.predict_proba(sample, **kwargs)
        else:
            return model.predict(sample, **kwargs)

    def response_from_prediction(self, y_pred, single=True):
        """Turns a model's prediction in *y_pred* into a JSON
        response.
        """
        result = y_pred.tolist()
        if single:
            result = result[0]
        response = {
            'metadata': get_metadata(),
            'result': result,
            }
        return make_ujson_response(response, status_code=200)

    def response_from_exception(self, exc):
        if isinstance(exc, PredictError):
            return make_ujson_response({
                'metadata': get_metadata(
                    error_code=exc.error_code,
                    error_message=exc.error_message,
                    status="ERROR"
                )
            }, status_code=500)
        elif isinstance(exc, BadRequest):
            return make_ujson_response({
                'metadata': get_metadata(
                    error_code=-1,
                    error_message="BadRequest: {}".format(exc.args),
                    status="ERROR"
                )
            }, status_code=400)
        else:
            logger.exception("Unexpected error")
            return make_ujson_response({
                'metadata': get_metadata(
                    error_code=-1,
                    error_message="{}: {}".format(
                        exc.__class__.__name__, str(exc)),
                    status="ERROR"
                )
            }, status_code=500)


@app.route('/predict', methods=['GET', 'POST'])
@PluggableDecorator('predict_decorators')
@args_from_config
def predict(model_persister, predict_service):
    try:
        model = model_persister.read()
        response = predict_service(model, request)
    except Exception as exc:
        logger.exception("Unexpected error")
        response = make_ujson_response({
            "status": "ERROR",
            "error_code": -1,
            "error_message": "{}: {}".format(exc.__class__.__name__, str(exc)),
        }, status_code=500)

    return response


@app.route('/alive')
@PluggableDecorator('alive_decorators')
@args_from_config
def alive(alive=None):
    if alive is None:
        alive = {}

    info = {
        'memory_usage': int(memory_usage_psutil()),
        'palladium_version': __version__,
        }

    info['service_metadata'] = get_config().get('service_metadata', {})

    status_code = 200
    for attr in alive.get('process_store_required', ()):
        obj = process_store.get(attr)
        if obj is not None:
            obj_info = {}
            obj_info['updated'] = process_store.mtime['model'].isoformat()
            if hasattr(obj, '__metadata__'):
                obj_info['metadata'] = obj.__metadata__
            info[attr] = obj_info
        else:
            info[attr] = "N/A"
            status_code = 503

    return make_ujson_response(info, status_code=status_code)


def devserver_cmd(argv=sys.argv[1:]):  # pragma: no cover
    __doc__ = """
Run a server for development.

Usage:
  pld-devserver [options]

Options:
  -h --help                  Show this screen.

  --host=<host>           The host to use [default: 0.0.0.0].

  --port=<port>           The port to use [default: 5000].

  --debug=<debug>         Whether or not to use debug mode [default: 0].
"""
    arguments = docopt(__doc__, argv=argv)
    initialize_config()
    app.run(
        host=arguments['--host'],
        port=int(arguments['--port']),
        debug=int(arguments['--debug']),
        )
