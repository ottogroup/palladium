"""Assorted utilties.
"""

from collections import UserDict
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from functools import wraps
import logging
from logging.config import dictConfig
from importlib import import_module
from inspect import getfullargspec
from inspect import getcallargs
import os
import sys
from threading import Thread
from time import sleep
from time import time

import dateutil.parser
import dateutil.rrule
from docopt import docopt
import psutil

from . import __version__


logger = logging.getLogger('palladium')


PALLADIUM_CONFIG_ERROR = """
  Maybe you forgot to set the environment variable PALLADIUM_CONFIG
  to point to your Palladium configuration file?  If so, please
  refer to the manual for more details.
"""


def resolve_dotted_name(dotted_name):
    if ':' in dotted_name:
        module, name = dotted_name.split(':')
    else:
        module, name = dotted_name.rsplit('.', 1)

    attr = import_module(module)
    for name in name.split('.'):
        attr = getattr(attr, name)

    return attr


def create_component(specification):
    specification = specification.copy()
    factory_dotted_name = specification.pop('__factory__')
    factory = resolve_dotted_name(factory_dotted_name)
    return factory(**specification)


class Config(dict):
    """A dictionary that represents the app's configuration.

    Tries to send a more user friendly message in case of KeyError.
    """
    initialized = False

    def __getitem__(self, name):
        try:
            return super(Config, self).__getitem__(name)
        except KeyError:
            raise KeyError(
                "The required key '{}' was not found in your "
                "configuration. {}".format(name, PALLADIUM_CONFIG_ERROR))

_config = Config()


def get_config(**extra):
    if not _config.initialized:
        _config.update(extra)
        _config.initialized = True
        fname = os.environ.get('PALLADIUM_CONFIG')
        if fname is not None:
            sys.path.insert(0, os.path.dirname(fname))

            with open(fname) as f:
                _config.update(
                    eval(f.read(), {'environ': os.environ})
                    )
                _initialize_config(_config)

    return _config


def initialize_config(**extra):
    if _config.initialized:
        raise RuntimeError("Configuration was already initialized")
    return get_config(**extra)


def _initialize_config_recursive(mapping):
    rv = []
    for key, value in tuple(mapping.items()):
        if isinstance(value, dict):
            rv.extend(_initialize_config_recursive(value))
            if '__factory__' in value:
                mapping[key] = create_component(value)
                rv.append(mapping[key])
        elif isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    rv.extend(_initialize_config_recursive(item))
                    if '__factory__' in item:
                        value[i] = create_component(item)
                        rv.append(value[i])
    return rv


def _initialize_config(config):
    components = []

    if 'logging' in config:
        dictConfig(config['logging'])
    else:
        logging.basicConfig(level=logging.DEBUG)

    components = _initialize_config_recursive(config)
    for component in components:
        if hasattr(component, 'initialize_component'):
            component.initialize_component(config)

    return config


def apply_kwargs(func, **kwargs):
    """Call *func* with kwargs, but only those kwargs that it accepts.
    """
    new_kwargs = {}
    func_args = getfullargspec(func)[0]
    for i, argname in enumerate(func_args):
        if argname in kwargs:
            new_kwargs[argname] = kwargs[argname]
    return func(**new_kwargs)


def args_from_config(func):
    """Decorator that injects parameters from the configuration.
    """
    func_args = getfullargspec(func)[0]

    @wraps(func)
    def wrapper(*args, **kwargs):
        config = get_config()
        for i, argname in enumerate(func_args):
            if len(args) > i or argname in kwargs:
                continue
            elif argname in config:
                kwargs[argname] = config[argname]
        try:
            getcallargs(func, *args, **kwargs)
        except TypeError as exc:
            msg = "{}\n{}".format(exc.args[0], PALLADIUM_CONFIG_ERROR)
            exc.args = (msg,)
            raise exc
        return func(*args, **kwargs)

    wrapper.__wrapped__ = func
    return wrapper


@contextmanager
def timer(log=None, message=None):
    if log is not None:
        log("{}...".format(message))

    info = {}
    t0 = time()
    yield info

    info['elapsed'] = time() - t0
    if log is not None:
        log("{} done in {:.3f} sec.".format(message, info['elapsed']))


@contextmanager
def session_scope(session):
    """Provide a transactional scope around a series of operations."""
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class ProcessStore(UserDict):
    def __init__(self, *args, **kwargs):
        self.mtime = {}
        super(ProcessStore, self).__init__(*args, **kwargs)

    def __setitem__(self, key, item):
        super(ProcessStore, self).__setitem__(key, item)
        self.mtime[key] = datetime.now()

    def __getitem__(self, key):
        return super(ProcessStore, self).__getitem__(key)

    def __delitem__(self, key):
        super(ProcessStore, self).__delitem__(key)
        del self.mtime[key]


process_store = ProcessStore()


class RruleThread(Thread):
    """Calls a given function in intervals defined by given recurrence
    rules (from `datetuil.rrule`).
    """
    def __init__(self, func, rrule, sleep_between_checks=60):
        """
        :param callable func:
          The function that I will call periodically.

        :param rrule rrule:

          The :class:`dateutil.rrule.rrule` recurrence rule that
          defines when I will do the calls.  See the `python-dateutil
          docs <https://labix.org/python-dateutil>`_ for details on
          how to define rrules.

          For convenience, I will also accept a dict instead of a
          `rrule` instance, in which case I will instantiate an rrule
          using the dict contents as keyword parameters.

        :param int sleep_between_checks:
          Number of seconds to sleep before I check again if I should
          run the function *func*.
        """
        super(RruleThread, self).__init__(daemon=True)
        if isinstance(rrule, dict):
            rrule = self._rrule_from_dict(rrule)
        self.func = func
        self.rrule = rrule
        self.sleep_between_checks = sleep_between_checks
        self.last_execution = datetime.now()
        self.alive = True

    @classmethod
    def _rrule_from_dict(cls, rrule):
        kwargs = rrule.copy()
        for key, value in rrule.items():
            # Allow constants in datetutil.rrule to be passed as strings
            if isinstance(value, str) and hasattr(dateutil.rrule, value):
                kwargs[key] = getattr(dateutil.rrule, value)

        dstart = kwargs.get('dtstart')
        if isinstance(dstart, str):
            kwargs['dtstart'] = dateutil.parser.parse(dstart)
        return dateutil.rrule.rrule(**kwargs)

    def run(self):
        while self.alive:
            now = datetime.now()
            if not self.rrule.between(self.last_execution, now):
                sleep(self.sleep_between_checks)
                continue

            self.last_execution = now

            try:
                self.func()
            except:
                logger.exception(
                    "Failed to call {}".format(self.func.__name__))


def memory_usage_psutil():
    """Return the current process memory usage in MB.
    """
    process = psutil.Process(os.getpid())
    mem = process.get_memory_info()[0] / float(2 ** 20)
    return mem


def version_cmd(argv=sys.argv[1:]):  # pragma: no cover
    __doc__ = """
Print the version number of Palladium.

Usage:
  palladium-version [options]

Options:
  -h --help                Show this screen.
"""
    docopt(__doc__, argv=argv)
    print(__version__)


class PluggableDecorator:
    def __init__(self, decorator_config_name):
        self.decorator_config_name = decorator_config_name
        self.wrapped = None

    def __call__(self, func):
        self.func = func

        def wrapper(*args, **kwargs):
            # The motivation here is that we want to defer loading the
            # configuration until the function is called for the first
            # time.
            if self.wrapped is None:
                func = self.func
                decorators = get_config().get(
                    self.decorator_config_name, [])
                self.decorators = [
                    resolve_dotted_name(dec) if isinstance(dec, str) else dec
                    for dec in decorators
                    ]
                orig_func = func
                for decorator in self.decorators:
                    func = decorator(func)
                if self.decorators:
                    self.wrapped = wraps(orig_func)(func)
                else:
                    self.wrapped = orig_func
            return self.wrapped(*args, **kwargs)

        return wraps(func)(wrapper)


def get_metadata(error_code=0, error_message=None, status='OK'):
    metadata = {
        'status': status,
        'error_code': error_code,
    }
    if error_message is not None:
        metadata['error_message'] = error_message
    metadata.update(get_config().get('service_metadata', {}))
    return metadata


def Partial(func, **kwargs):
    """Allows the use of partially applied functions in the
    configuration.
    """
    if isinstance(func, str):
        func = resolve_dotted_name(func)
    return partial(func, **kwargs)
