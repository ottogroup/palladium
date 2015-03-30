from unittest.mock import Mock
from unittest.mock import patch

import pytest


class TestTest:
    @pytest.fixture
    def test(self):
        from palladium.eval import test
        return test

    def test_test(self, test):
        dataset_loader_test, model_persister = Mock(), Mock()
        X, y = object(), object()
        dataset_loader_test.return_value = X, y
        model = model_persister.read.return_value
        model.__metadata__ = {'version': 77}

        test(dataset_loader_test, model_persister, model_version=77)

        dataset_loader_test.assert_called_with()
        model_persister.read.assert_called_with(version=77)
        model.score.assert_called_with(X, y)

    def test_test_no_score(self, test):
        dataset_loader_test, model_persister = Mock(), Mock()
        X, y = object(), object()
        dataset_loader_test.return_value = X, y
        model_persister.read.return_value = Mock(spec=['fit', 'predict'])
        model_persister.read.return_value.__metadata__ = {'version': 99}

        with pytest.raises(ValueError):
            test(dataset_loader_test, model_persister)


class TestList:
    @pytest.fixture
    def list(self):
        from palladium.eval import list
        return list

    def test(self, list):
        model_persister = Mock()
        model_persister.list.return_value = [{1: 2}]
        with patch('palladium.eval.pprint') as pprint:
            list(model_persister)
        pprint.assert_called_with([{1: 2}])
