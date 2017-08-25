import logging
from logging.config import dictConfig
import os
import sys


PALLADIUM_CONFIG_ERROR = """
  Maybe you forgot to set the environment variable PALLADIUM_CONFIG
  to point to your Palladium configuration file?  If so, please
  refer to the manual for more details.
"""


def create_component(specification):
    from .util import resolve_dotted_name
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
        fnames = os.environ.get('PALLADIUM_CONFIG')
        if fnames is not None:
            fnames = [fname.strip() for fname in fnames.split(',')]
            sys.path.insert(0, os.path.dirname(fnames[0]))
            for fname in fnames:
                with open(fname) as f:
                    _config.update(
                        eval(f.read(), {
                            'environ': os.environ,
                            'here': os.path.abspath(os.path.dirname(fname)),
                            })
                        )
            _initialize_config(_config)

    return _config


def initialize_config(**extra):
    if _config.initialized:
        raise RuntimeError("Configuration was already initialized")
    return get_config(**extra)


def _initialize_config_recursive(props):
    rv = []
    if isinstance(props, dict):
        for key, value in tuple(props.items()):
            if isinstance(value, dict):
                rv.extend(_initialize_config_recursive(value))
                if '__factory__' in value:
                    props[key] = create_component(value)
                    rv.append(props[key])
            elif isinstance(value, (list, tuple)):
                rv.extend(_initialize_config_recursive(value))
    elif isinstance(props, (list, tuple)):
        for i, item in enumerate(props):
            if isinstance(item, dict):
                rv.extend(_initialize_config_recursive(item))
                if '__factory__' in item:
                    props[i] = create_component(item)
                    rv.append(props[i])
            elif isinstance(item, (list, tuple)):
                rv.extend(_initialize_config_recursive(item))
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
