"""Utilities for testing the performance of a trained model.
"""

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
    __doc__ = """
Test a model.

Usage:
  palladium-test [options]

Options:
  -h --help                  Show this screen.

  --model-version=<version>  The version of the model to be tested. If
                             not specified, the newest model will be used.
"""
    arguments = docopt(__doc__, argv=argv)
    model_version = arguments['--model-version']
    model_version = int(model_version) if model_version is not None else None
    initialize_config(__mode__='fit')
    test(model_version=model_version)


@args_from_config
def list(model_persister):
    pprint(model_persister.list())


def list_cmd(argv=sys.argv[1:]):  # pragma: no cover
    __doc__ = """
List information about available models.

Usage:
  palladium-list [options]

Options:
  -h --help                  Show this screen.
"""
    docopt(__doc__, argv=argv)
    initialize_config(__mode__='fit')
    list()
