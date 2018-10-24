import os
import readline  # https://github.com/ContinuumIO/anaconda-issues/issues/152

import pytest

from palladium.tests import run_smoke_tests_with_config


pytest.importorskip("rpy2")
pytest_plugins = 'palladium'


config2path = {
    'config-iris.py': '/predict?'
    'sepal length=1.0&sepal width=1.1&petal length=0.777&petal width=5',

    'config-iris.py,config-iris-dataset-from-python.py': '/predict?'
    'sepal length=1.0&sepal width=1.1&petal length=0.777&petal width=5',

    'config-tooth.py': '/predict?'
    'supp=OJ&dose=0.5',
    }


@pytest.mark.slow
@pytest.mark.parametrize(
    'config_filename', [
        'config-iris.py',
        'config-iris.py,config-iris-dataset-from-python.py',
        'config-tooth.py',
        ],
    )
def test_functional(flask_app_test, config_filename):
    config_fname = os.path.join(
        os.path.dirname(__file__),
        config_filename,
    )
    with flask_app_test.test_request_context():
        run_smoke_tests_with_config(
            config_fname,
            run=['fit', 'test', 'predict'],
            func_kwargs={'predict': {'path': config2path[config_filename]}},
            )
