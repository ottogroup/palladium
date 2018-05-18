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
from .fit import activate as activate_base
from .fit import fit as fit_base
from .interfaces import PredictError
from .util import args_from_config
from .util import get_config
from .util import get_metadata
from .util import initialize_config
from .util import logger
from .util import memory_usage_psutil
from .util import PluggableDecorator
from .util import process_store
from .util import run_job
from .util import resolve_dotted_name

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

    def __init__(
            self, mapping, params=(), entry_point='/predict',
            decorator_list_name='predict_decorators',
            predict_proba=False, **kwargs):
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
        self.entry_point = entry_point
        self.decorator_list_name = decorator_list_name
        self.predict_proba = predict_proba
        vars(self).update(kwargs)

    def initialize_component(self, config):
        create_predict_function(
            self.entry_point, self, self.decorator_list_name, config)

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

    mem, mem_vms = memory_usage_psutil()
    info = {
        'memory_usage': mem,  # rss, resident set size
        'memory_usage_vms': mem_vms,  # vms, virtual memory size
        'palladium_version': __version__,
    }

    info['service_metadata'] = get_config().get('service_metadata', {})

    status_code = 200
    for attr in alive.get('process_store_required', ()):
        obj = process_store.get(attr)
        if obj is not None:
            obj_info = {}
            obj_info['updated'] = process_store.mtime[attr].isoformat()
            if hasattr(obj, '__metadata__'):
                obj_info['metadata'] = obj.__metadata__
            info[attr] = obj_info
        else:
            info[attr] = "N/A"
            status_code = 503

    info['process_metadata'] = process_store['process_metadata']

    return make_ujson_response(info, status_code=status_code)


def create_predict_function(
        route, predict_service, decorator_list_name, config):
    """Creates a predict function and registers it to
    the Flask app using the route decorator.

    :param str route:
      Path of the entry point.

    :param palladium.interfaces.PredictService predict_service:
      The predict service to be registered to this entry point.

    :param str decorator_list_name:
      The decorator list to be used for this predict service. It is
      OK if there is no such entry in the active Palladium config.

    :return:
      A predict service function that will be used to process
      predict requests.
    """
    model_persister = config.get('model_persister')

    @app.route(route, methods=['GET', 'POST'], endpoint=route)
    @PluggableDecorator(decorator_list_name)
    def predict_func():
        return predict(model_persister, predict_service)

    return predict_func


def devserver_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Serve the web API for development.

Usage:
  pld-devserver [options]

Options:
  -h --help               Show this screen.

  --host=<host>           The host to use [default: 0.0.0.0].

  --port=<port>           The port to use [default: 5000].

  --debug=<debug>         Whether or not to use debug mode [default: 0].
"""
    arguments = docopt(devserver_cmd.__doc__, argv=argv)
    initialize_config()
    app.run(
        host=arguments['--host'],
        port=int(arguments['--port']),
        debug=int(arguments['--debug']),
        )


class PredictStream:
    """A class that helps make predictions through stdin and stdout.
    """
    def __init__(self):
        self.model = get_config()['model_persister'].read()
        self.predict_service = get_config()['predict_service']

    def process_line(self, line):
        predict_service = self.predict_service
        datas = ujson.loads(line)
        samples = [predict_service.sample_from_data(self.model, data)
                   for data in datas]
        samples = np.array(samples)
        params = predict_service.params_from_data(self.model, datas[0])
        return predict_service.predict(self.model, samples, **params)

    def listen(self, io_in, io_out, io_err):
        """Listens to provided io stream and writes predictions
        to output. In case of errors, the error stream will be used.
        """
        for line in io_in:
            if line.strip().lower() == 'exit':
                break

            try:
                y_pred = self.process_line(line)
            except Exception as e:
                io_out.write('[]\n')
                io_err.write(
                    "Error while processing input row: {}"
                    "{}: {}\n".format(line, type(e), e))
                io_err.flush()
            else:
                io_out.write(ujson.dumps(y_pred.tolist()))
                io_out.write('\n')
                io_out.flush()


def stream_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Start the streaming server, which listens to stdin, processes line
by line, and returns predictions.

The input should consist of a list of json objects, where each object
will result in a prediction.  Each line is processed in a batch.

Example input (must be on a single line):

  [{"sepal length": 1.0, "sepal width": 1.1, "petal length": 0.7,
    "petal width": 5}, {"sepal length": 1.0, "sepal width": 8.0,
    "petal length": 1.4, "petal width": 5}]

Example output:

  ["Iris-virginica","Iris-setosa"]

An input line with the word 'exit' will quit the streaming server.

Usage:
  pld-stream [options]

Options:
  -h --help                  Show this screen.
"""
    docopt(stream_cmd.__doc__, argv=argv)
    initialize_config()
    stream = PredictStream()
    stream.listen(sys.stdin, sys.stdout, sys.stderr)


@app.route('/list')
@PluggableDecorator('list_decorators')
@args_from_config
def list(model_persister):
    info = {
        'models': model_persister.list_models(),
        'properties': model_persister.list_properties(),
        }
    return make_ujson_response(info)


@PluggableDecorator('server_fit_decorators')
@args_from_config
def fit():
    param_converters = {
        'persist': lambda x: x.lower() in ('1', 't', 'true'),
        'activate': lambda x: x.lower() in ('1', 't', 'true'),
        'evaluate': lambda x: x.lower() in ('1', 't', 'true'),
        'persist_if_better_than': float,
        }
    params = {
        name: typ(request.form[name])
        for name, typ in param_converters.items()
        if name in request.form
        }
    thread, job_id = run_job(fit_base, **params)
    return make_ujson_response({'job_id': job_id}, status_code=200)


@PluggableDecorator('update_model_cache_decorators')
@args_from_config
def update_model_cache(model_persister):
    method = getattr(model_persister, 'update_cache', None)
    if method is not None:
        thread, job_id = run_job(model_persister.update_cache)
        return make_ujson_response({'job_id': job_id}, status_code=200)
    else:
        return make_ujson_response({}, status_code=503)


@PluggableDecorator('activate_decorators')
def activate():
    model_version = int(request.form['model_version'])
    try:
        activate_base(model_version=model_version)
    except LookupError:
        return make_ujson_response({}, status_code=503)
    else:
        return list()


def add_url_rule(rule, endpoint=None, view_func=None, app=app, **options):
    if isinstance(view_func, str):
        view_func = resolve_dotted_name(view_func)
    app.add_url_rule(rule, endpoint=endpoint, view_func=view_func, **options)
