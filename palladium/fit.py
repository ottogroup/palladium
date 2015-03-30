"""Utilities for fitting modles.
"""

import sys

from datetime import datetime
from docopt import docopt
from pprint import pformat
from sklearn.grid_search import GridSearchCV

from .interfaces import annotate
from .util import apply_kwargs
from .util import args_from_config
from .util import initialize_config
from .util import logger
from .util import PluggableDecorator
from .util import timer


@PluggableDecorator('fit_decorators')
@args_from_config
def fit(dataset_loader_train, model, model_persister, persist=True,
        dataset_loader_test=None, evaluate=False, persist_if_better_than=None):

    if persist_if_better_than is not None:
        evaluate = True
        if dataset_loader_test is None:
            raise ValueError(
                "When using 'persist_if_better_than', make sure you also "
                "provide a 'dataset_loader_test'."
                )

    with timer(logger.info, "Loading data"):
        X, y = dataset_loader_train()

    with timer(logger.info, "Fitting model"):
        model.fit(X, y)

    if evaluate:
        with timer(logger.debug, "Evaluating model on train set"):
            score_train = model.score(X, y)
            annotate(model, {'score_train': score_train})
            logger.info("Train score: {}".format(score_train))

    score_test = None
    if evaluate and dataset_loader_test is not None:
        X_test, y_test = dataset_loader_test()
        with timer(logger.debug, "Evaluating model on test set"):
            score_test = model.score(X_test, y_test)
            annotate(model, {'score_test': score_test})
            logger.info("Test score:  {}".format(score_test))

    if persist:
        if (persist_if_better_than is not None and
            score_test < persist_if_better_than):
            logger.info("Not persisting model that has a test score "
                        "{} < {}".format(score_test, persist_if_better_than))
        else:
            annotate(model, {'train_timestamp': datetime.now().isoformat()})
            with timer(logger.info, "Writing model"):
                version = model_persister.write(model)
            logger.info("Wrote model with version {}.".format(version))

    return model


def fit_cmd(argv=sys.argv[1:]):  # pragma: no cover
    __doc__ = """
Fit a model and save to database.

Usage:
  palladium-fit [options]

Options:
  -n --no-save              Don't persist the fitted model to disk.

  --save-if-better-than=<k> Persist only if test score better than given
                            value.

  -e --evaluate             Evaluate fitted model on train and test set and
                            print out results.

  -h --help                 Show this screen.
"""
    arguments = docopt(__doc__, argv=argv)
    no_save = arguments['--no-save']
    save_if_better_than = arguments['--save-if-better-than']
    evaluate = arguments['--evaluate'] or bool(save_if_better_than)
    if save_if_better_than is not None:
        save_if_better_than = float(save_if_better_than)
    initialize_config(__mode__='fit')
    fit(
        persist=not no_save,
        evaluate=evaluate,
        persist_if_better_than=save_if_better_than,
        )


@args_from_config
def grid_search(dataset_loader_train, model, grid_search):
    with timer(logger.info, "Loading data"):
        X, y = dataset_loader_train()

    grid_search_kwargs = {
        'refit': False,
        }
    grid_search_kwargs.update(grid_search)

    cv = grid_search_kwargs.get('cv', None)
    if callable(cv):
        grid_search_kwargs['cv'] = apply_kwargs(cv, n=len(y), y=y)

    if not (hasattr(model, 'score') or 'scoring' in grid_search_kwargs):
        raise ValueError(
            "Your model doesn't seem to implement a 'score' method.  You may "
            "want to pass a 'scoring' argument to 'grid_search' instead."
            )

    with timer(logger.info, "Running grid search"):
        gs = GridSearchCV(model, **grid_search_kwargs)
        gs.fit(X, y)

    scores = sorted(gs.grid_scores_, key=lambda x: -x.mean_validation_score)
    logger.info("\n{}".format(pformat(scores)))
    return scores


def grid_search_cmd(argv=sys.argv[1:]):  # pragma: no cover
    __doc__ = """
Grid search parameters for the model.

Usage:
  palladium-grid-search [options]

Options:
  -h --help                Show this screen.
"""
    docopt(__doc__, argv=argv)
    initialize_config(__mode__='fit')
    grid_search()
