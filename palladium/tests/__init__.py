from collections import OrderedDict
from contextlib import contextmanager
import os
from random import shuffle
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def config(request):
    from palladium.config import _config

    orig = _config.copy()
    _config.clear()
    _config.initialized = False
    request.addfinalizer(
        lambda: (_config.clear(), _config.update(orig)))
    return _config


@pytest.fixture
def flask_app(config):
    from palladium.server import app
    return app


def _reset_url_map(
        app, orig_rules, orig_rules_by_endpoint, orig_view_functions,
        orig_remap):
    app.url_map._rules = orig_rules
    app.url_map._rules_by_endpoint = orig_rules_by_endpoint
    app.view_functions = orig_view_functions
    app.url_map._remap = True
    app.url_map.update()
    app.url_map._remap = orig_remap


@pytest.fixture
def flask_app_test(request, config):
    """A Flask app where _url_map, _view_functions, _rules, and
    _rules_by_end_point will be reset to the previous values after
    running the test.
    """
    from palladium.server import app

    orig_rules = app.url_map._rules
    app.url_map._rules = [rule for rule in app.url_map._rules]
    orig_rules_by_endpoint = app.url_map._rules_by_endpoint
    app.url_map._rules_by_endpoint = {
        k: v for k, v in app.url_map._rules_by_endpoint.items()}
    orig_view_functions = app.view_functions
    app.view_functions = {
        k: v for (k, v) in app.view_functions.items()}
    orig_remap = app.url_map._remap
    request.addfinalizer(
        lambda: (
            _reset_url_map(
                app, orig_rules, orig_rules_by_endpoint, orig_view_functions,
                orig_remap))
    )
    return app


@contextmanager
def change_cwd(path):
    cwd = os.getcwd()
    if path:
        os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def predict(
        path='/predict?sepal length=1.0&sepal width=1.1&'
             'petal length=0.777&petal width=5',
        predict_service_name='predict_service'):
    from palladium.server import app
    from palladium.server import predict
    from palladium.util import get_config

    model_persister = get_config()['model_persister']
    predict_service = get_config()[predict_service_name]

    with app.test_request_context(path):
        response = predict(model_persister, predict_service)
        assert response.status_code == 200


def run_smoke_tests_with_config(config_fname, run=None, raise_errors=True,
                                func_kwargs=None, cwd=True):
    from palladium.util import logger  # don't break coverage
    from palladium.util import timer

    if func_kwargs is None:
        func_kwargs = {}

    print("Running functional tests for {}".format(config_fname))

    with patch.dict('os.environ', {'PALLADIUM_CONFIG': config_fname}):
        from palladium.fit import fit
        from palladium.fit import activate
        from palladium.fit import grid_search
        from palladium.eval import test
        from palladium.util import initialize_config

        failed = []

        if cwd:
            cwd = change_cwd(os.path.dirname(config_fname))
        else:
            cwd = MagicMock()

        with cwd:
            initialize_config(__mode__='fit')
            for func in (fit, activate, grid_search, test, predict):
                if run and func.__name__ not in run:
                    continue
                try:
                    this_kwargs = func_kwargs.get(func.__name__, {})
                    with timer(logger.info,
                               "Running {}".format(func.__name__)):
                        func(**this_kwargs)
                except Exception as e:
                    if raise_errors:
                        raise
                    failed.append((func.__name__, e))

    return failed


def pytest_configure(config):
    # Don't allow accidental PALLADIUM_CONFIGs to leak into tests:
    os.environ.pop('PALLADIUM_CONFIG', None)


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="run slow tests")


def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getoption("--runslow"):
        pytest.skip("need --runslow option to run")
