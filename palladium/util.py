"""Assorted utilties.
"""

from collections import UserDict
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from functools import update_wrapper
from functools import wraps
import logging
from importlib import import_module
from inspect import signature
from inspect import getcallargs
import os
import sys
import threading
from time import sleep
from time import time
import traceback
import uuid

import dateutil.parser
import dateutil.rrule
from docopt import docopt
import psutil

from . import __version__
from .config import get_config
from .config import initialize_config
from .config import PALLADIUM_CONFIG_ERROR

logger = logging.getLogger('palladium')


def resolve_dotted_name(dotted_name):
    if ':' in dotted_name:
        module, name = dotted_name.split(':')
    else:
        module, name = dotted_name.rsplit('.', 1)

    attr = import_module(module)
    for name in name.split('.'):
        attr = getattr(attr, name)

    return attr


def apply_kwargs(func, **kwargs):
    """Call *func* with kwargs, but only those kwargs that it accepts.
    """
    new_kwargs = {}
    params = signature(func).parameters
    for param_name in params.keys():
        if param_name in kwargs:
            new_kwargs[param_name] = kwargs[param_name]
    return func(**new_kwargs)


def args_from_config(func):
    """Decorator that injects parameters from the configuration.
    """
    func_args = signature(func).parameters

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


process_store = ProcessStore(process_metadata={})


class RruleThread(threading.Thread):
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
    mem = process.memory_info()[0] / float(2 ** 20)
    mem_vms = process.memory_info()[1] / float(2 ** 20)
    return mem, mem_vms


def version_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Print the version number of Palladium.

Usage:
  pld-version [options]

Options:
  -h --help                Show this screen.
"""
    docopt(version_cmd.__doc__, argv=argv)
    print(__version__)


@args_from_config
def upgrade(model_persister, from_version=None, to_version=None):
    kwargs = {'from_version': from_version}
    if to_version is not None:
        kwargs['to_version'] = to_version
    model_persister.upgrade(**kwargs)


def upgrade_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Upgrade the database to the latest version.

Usage:
  pld-ugprade [options]

Options:
  --from=<v>               Upgrade from a specific version, overriding
                           the version stored in the database.

  --to=<v>                 Upgrade to a specific version instead of the
                           latest version.

  -h --help                Show this screen.
"""
    arguments = docopt(upgrade_cmd.__doc__, argv=argv)
    initialize_config(__mode__='fit')
    upgrade(from_version=arguments['--from'], to_version=arguments['--to'])


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


@PluggableDecorator('get_metadata_decorators')
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
    partial_func = partial(func, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func


def _run_job(func, job_id, params):
    jobs = process_store['process_metadata'].setdefault('jobs', {})
    job = jobs[job_id] = {
        'func': repr(func),
        'started': str(datetime.utcnow()),
        'status': 'running',
        'thread': threading.get_ident(),
        }
    try:
        retval = func(**params)
    except:
        job['status'] = 'error'
        job['info'] = traceback.format_exc()
    else:
        job['status'] = 'finished'
        job['info'] = str(retval)


def run_job(func, **params):
    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_job,
        kwargs={'func': func, 'job_id': job_id, 'params': params},
        )
    thread.start()
    return thread, job_id
