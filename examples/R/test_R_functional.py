import os
import readline  # https://github.com/ContinuumIO/anaconda-issues/issues/152

import pytest

from palladium.tests import run_smoke_tests_with_config


pytest.importorskip("rpy2")
pytest_plugins = 'palladium'


@pytest.mark.slow
def test_functional(flask_app_test):
    config_fname = os.path.join(
        os.path.dirname(__file__),
        'config.py',
    )
    with flask_app_test.test_request_context():
        run_smoke_tests_with_config(
            config_fname, run=['fit', 'test', 'predict'])


if __name__ == '__main__':
    test_functional()
