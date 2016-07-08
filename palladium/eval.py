"""Utilities for testing the performance of a trained model.
"""

from code import InteractiveConsole
from pprint import pformat
from pprint import pprint
import sys

from docopt import docopt

from .util import args_from_config
from .util import initialize_config
from .util import logger
from .util import timer


@args_from_config
def test(dataset_loader_test, model_persister, model_version=None):

    with timer(logger.info, "Loading data"):
        X, y = dataset_loader_test()

    with timer(logger.info, "Reading model"):
        model = model_persister.read(version=model_version)

    logger.info(
        'Loaded model version {}'.format(model.__metadata__['version']))

    if not hasattr(model, 'score'):
        raise ValueError(
            "Your model doesn't seem to implement a 'score' method."
            )

    with timer(logger.info, "Applying model"):
        score = model.score(X, y)

    logger.info("Score: {}.".format(score))


def test_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Test a model.

Uses 'dataset_loader_test' and 'model_persister' from the
configuration to load a test dataset to test the accuracy of a trained
model with.

Usage:
  pld-test [options]

Options:
  -h --help                  Show this screen.

  --model-version=<version>  The version of the model to be tested. If
                             not specified, the newest model will be used.
"""
    arguments = docopt(test_cmd.__doc__, argv=argv)
    model_version = arguments['--model-version']
    model_version = int(model_version) if model_version is not None else None
    initialize_config(__mode__='fit')
    test(model_version=model_version)


@args_from_config
def list(model_persister):
    print("Models:")
    pprint(model_persister.list_models())
    print("Properties:")
    pprint(model_persister.list_properties())


def list_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
List information about available models.

Uses the 'model_persister' from the configuration to display a list of
models and their metadata.

Usage:
  pld-list [options]

Options:
  -h --help                  Show this screen.
"""
    docopt(list_cmd.__doc__, argv=argv)
    initialize_config(__mode__='fit')
    list()


def shell_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
A Python shell that has all configuration loaded into the namespace.

Usage:
  pld-shell [options]

Options:
  -h --help                  Show this screen.
"""
    docopt(list_cmd.__doc__, argv=argv)
    config = initialize_config(__mode__='fit')
    banner = """\
Welcome to the palladium shell.  I've loaded your configuration for you,
and here's the variables you have access to:
{}
""".format(pformat(config))
    InteractiveConsole(config).interact(banner=banner)
