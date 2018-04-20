from unittest.mock import Mock
from unittest.mock import call
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

    def test_test_two_scores(self, test):
        dataset_loader_test, model_persister, scorer = Mock(), Mock(), Mock()
        X, y = object(), object()
        dataset_loader_test.return_value = X, y
        model = model_persister.read.return_value
        model.__metadata__ = {'version': 77}

        test(dataset_loader_test, model_persister,
             scoring=scorer, model_version=77)

        dataset_loader_test.assert_called_with()
        model_persister.read.assert_called_with(version=77)
        scorer.assert_called_with(model, X, y)
        assert model.score.call_count == 0

    def test_scoring_dict(self, test):
        dataset_loader_test, model_persister = Mock(), Mock()
        scoring = {'AUC': Mock(), 'accuracy': Mock()}
        scoring['AUC'].return_value = 1.23
        scoring['accuracy'].return_value = 3.45
        X, y = object(), object()
        dataset_loader_test.return_value = X, y
        model = model_persister.read.return_value
        model.__metadata__ = {'version': 77}

        result = test(dataset_loader_test, model_persister,
                      scoring=scoring, model_version=77)

        scoring['AUC'].assert_called_with(model, X, y)
        scoring['accuracy'].assert_called_with(model, X, y)
        assert sorted(result) == ['AUC: 1.23', 'accuracy: 3.45']


class TestList:
    @pytest.fixture
    def list(self):
        from palladium.eval import list
        return list

    def test(self, list):
        model_persister = Mock()
        model_persister.list_models.return_value = [{1: 2}]
        model_persister.list_properties.return_value = {5: 6}
        with patch('palladium.eval.pprint') as pprint:
            list(model_persister)
        assert pprint.mock_calls[0] == call([{1: 2}])
        assert pprint.mock_calls[1] == call({5: 6})
