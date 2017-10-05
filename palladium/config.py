from copy import deepcopy
import logging
from logging.config import dictConfig
import os
import sys
import threading


PALLADIUM_CONFIG_ERROR = """
  Maybe you forgot to set the environment variable PALLADIUM_CONFIG
  to point to your Palladium configuration file?  If so, please
  refer to the manual for more details.
"""


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


class ComponentHandler:
    key = '__factory__'

    def __init__(self, config):
        self.config = config
        self.components = []

    def __call__(self, name, props):
        from .util import resolve_dotted_name
        specification = props.copy()
        factory_dotted_name = specification.pop(self.key)
        factory = resolve_dotted_name(factory_dotted_name)
        component = factory(**specification)
        try:
            component.__pld_config_key__ = name
        except AttributeError:
            pass
        self.components.append(component)
        return component

    def finish(self):
        for component in self.components:
            if hasattr(component, 'initialize_component'):
                component.initialize_component(self.config)


class CopyHandler:
    key = '__copy__'

    def __init__(self, configs):
        self.configs = configs

    @staticmethod
    def _resolve(configs, dotted_path):
        for config in configs[::-1]:
            value = config
            for part in dotted_path.split('.'):
                try:
                    value = value[part]
                except KeyError:
                    break
            else:
                return value
        else:
            raise KeyError(dotted_path)

    def __call__(self, name, props):
        dotted_path = props[self.key]
        try:
            value = self._resolve(self.configs[-1:], dotted_path)
            self_reference = value is props
        except KeyError:
            self_reference = False

        if self_reference:
            value = self._resolve(self.configs[:-1], dotted_path)
        else:
            value = self._resolve(self.configs, dotted_path)

        value = deepcopy(value)
        if len(props) > 1:
            recursive_copy = self.key in value
            value.update(props)
            if not recursive_copy:
                del value[self.key]
        return value


class PythonHandler:
    key = '__python__'

    def __init__(self, config):
        self.config = config

    def __call__(self, name, props):
        statements = props.pop(self.key)
        exec(
            statements,
            globals(),
            {key: self.config for key in ['C', 'cfg', 'config']},
            )
        return props


def _handlers_phase0(configs):
    return {
        Handler.key: Handler(configs) for Handler in [
            CopyHandler,
            ]
        }


def _handlers_phase1(config):
    return {
        Handler.key: Handler(config) for Handler in [
            PythonHandler,
            ]
        }


def _handlers_phase2(config):
    return {
        Handler.key: Handler(config) for Handler in [
            ComponentHandler,
            ]
        }


def _run_config_handlers_recursive(props, handlers):
    if isinstance(props, dict):
        for key, value in tuple(props.items()):
            if isinstance(value, dict):
                _run_config_handlers_recursive(value, handlers)
                for name, handler in handlers.items():
                    if name in value:
                        value = props[key] = handler(key, value)
            elif isinstance(value, (list, tuple)):
                _run_config_handlers_recursive(value, handlers)
    elif isinstance(props, (list, tuple)):
        for i, item in enumerate(props):
            if isinstance(item, dict):
                _run_config_handlers_recursive(item, handlers)
                for name, handler in handlers.items():
                    if name in item:
                        item = props[i] = handler(str(i), item)
            elif isinstance(item, (list, tuple)):
                _run_config_handlers_recursive(item, handlers)


def _run_config_handlers(config, handlers):
    wrapped_config = {'root': config}
    _run_config_handlers_recursive(wrapped_config, handlers)
    for handler in handlers.values():
        if hasattr(handler, 'finish'):
            handler.finish()
    return wrapped_config['root']


def _initialize_logging(config):
    if 'logging' in config:
        dictConfig(config['logging'])
    else:
        logging.basicConfig(level=logging.DEBUG)


def process_config(
    *configs,
    handlers0=_handlers_phase0,
    handlers1=_handlers_phase1,
    handlers2=_handlers_phase2
):
    config_final = {}

    for config in configs:
        config_org = deepcopy(config_final)
        config_final.update(config)
        _run_config_handlers(
            config_final, handlers0([config_org, config]))
        _run_config_handlers(
            config_final, handlers0([config_final, {}]))

    _run_config_handlers(config_final, handlers1(config_final))
    _run_config_handlers(config_final, handlers2(config_final))
    _initialize_logging(config_final)
    return config_final


_get_config_lock = threading.RLock()


def get_config(**extra):
    with _get_config_lock:
        config = _get_config(**extra)
    return config


def _get_config(**extra):
    if not _config.initialized:
        _config.update(extra)
        _config.initialized = True
        fnames = os.environ.get('PALLADIUM_CONFIG')
        if fnames is not None:
            configs = []
            fnames = [fname.strip() for fname in fnames.split(',')]
            for fname in fnames:
                sys.path.insert(0, os.path.dirname(fname))
                with open(fname) as f:
                    config = eval(f.read(), {
                        'environ': os.environ,
                        'here': os.path.abspath(os.path.dirname(fname)),
                        })
                configs.append(config)
            _config.update(process_config(_config, *configs))
    return _config


def initialize_config(**extra):
    if _config.initialized:
        raise RuntimeError("Configuration was already initialized")
    return get_config(**extra)
