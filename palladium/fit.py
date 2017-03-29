"""Utilities for fitting modles.
"""

import sys

from datetime import datetime
from docopt import docopt
from pprint import pformat
from sklearn.model_selection import GridSearchCV

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
        activate=True, dataset_loader_test=None, evaluate=False,
        persist_if_better_than=None):

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
            if activate:
                model_persister.activate(version)

    return model


def fit_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Fit a model and save to database.

Will use 'dataset_loader_train', 'model', and 'model_perister' from
the configuration file, to load a dataset to train a model with, and
persist it.

Usage:
  pld-fit [options]

Options:
  -n --no-save              Don't persist the fitted model to disk.

  --no-activate             Don't activate the fitted model.

  --save-if-better-than=<k> Persist only if test score better than given
                            value.

  -e --evaluate             Evaluate fitted model on train and test set and
                            print out results.

  -h --help                 Show this screen.
"""
    arguments = docopt(fit_cmd.__doc__, argv=argv)
    no_save = arguments['--no-save']
    no_activate = arguments['--no-activate']
    save_if_better_than = arguments['--save-if-better-than']
    evaluate = arguments['--evaluate'] or bool(save_if_better_than)
    if save_if_better_than is not None:
        save_if_better_than = float(save_if_better_than)
    initialize_config(__mode__='fit')
    fit(
        persist=not no_save,
        activate=not no_activate,
        evaluate=evaluate,
        persist_if_better_than=save_if_better_than,
        )


@args_from_config
def activate(model_persister, model_version):
    model_persister.activate(model_version)
    logger.info("Activated model with version {}.".format(model_version))


@args_from_config
def delete(model_persister, model_version):
    model_persister.delete(model_version)
    logger.info("Deleted model with version {}.".format(model_version))


def admin_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Activate or delete models.

Models are usually made active right after fitting (see command
pld-fit).  The 'activate' command allows you to explicitly set the
currently active model.  Use 'pld-list' to get an overview of all
available models along with their version identifiers.

Deleting a model will simply remove it from the database.

Usage:
  pld-admin activate <version> [options]
  pld-admin delete <version> [options]

Options:
  -h --help                 Show this screen.
"""
    arguments = docopt(admin_cmd.__doc__, argv=argv)
    initialize_config(__mode__='fit')
    if arguments['activate']:
        activate(model_version=int(arguments['<version>']))
    elif arguments['delete']:
        delete(model_version=int(arguments['<version>']))


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
        grid_search_kwargs['cv'] = apply_kwargs(cv, n=len(y), X=X, y=y)

    if not (hasattr(model, 'score') or 'scoring' in grid_search_kwargs):
        raise ValueError(
            "Your model doesn't seem to implement a 'score' method.  You may "
            "want to pass a 'scoring' argument to 'grid_search' instead."
            )

    with timer(logger.info, "Running grid search"):
        gs = GridSearchCV(model, **grid_search_kwargs)
        gs.fit(X, y)

    scores = []
    means = gs.cv_results_['mean_test_score']
    stds = gs.cv_results_['std_test_score']
    params = gs.cv_results_['params']
    for mean, std, param in zip(means, stds, params):
        scores.append("mean: {0:.5f}, std: {1:.5f}, params: {2}".format(mean, std, param))
    logger.info('\n{}'.format(
        pformat(sorted(scores, reverse=True)).replace('"', '')))
    return scores


def grid_search_cmd(argv=sys.argv[1:]):  # pragma: no cover
    """\
Grid search parameters for the model.

Uses 'dataset_loader_train', 'model', and 'grid_search' from the
configuration to load a training dataset, and run a grid search on the
model using the grid of hyperparameters.

Usage:
  pld-grid-search [options]

Options:
  -h --help                Show this screen.
"""
    docopt(grid_search_cmd.__doc__, argv=argv)
    initialize_config(__mode__='fit')
    grid_search()
