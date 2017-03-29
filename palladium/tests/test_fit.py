from datetime import datetime
from functools import partial
import numpy as np
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

from dateutil.parser import parse
import pytest


class TestFit:
    @pytest.fixture
    def fit(self):
        from palladium.fit import fit
        return fit

    @pytest.fixture
    def dataset_loader(self):
        dataset_loader = Mock()
        dataset_loader.return_value = Mock(), Mock()
        return dataset_loader

    def test_it(self, fit):
        model, dataset_loader_train, model_persister = Mock(), Mock(), Mock()
        X, y = object(), object()
        dataset_loader_train.return_value = X, y

        result = fit(dataset_loader_train, model, model_persister)

        assert result is model
        dataset_loader_train.assert_called_with()
        model.fit.assert_called_with(X, y)
        model_persister.write.assert_called_with(model)
        model_persister.activate.assert_called_with(
            model_persister.write.return_value)

    def test_no_persist(self, fit):
        model, dataset_loader_train, model_persister = Mock(), Mock(), Mock()
        X, y = object(), object()
        dataset_loader_train.return_value = X, y

        result = fit(dataset_loader_train, model, model_persister,
                     persist=False)

        assert result is model
        dataset_loader_train.assert_called_with()
        model.fit.assert_called_with(X, y)
        assert model_persister.call_count == 0

    def test_evaluate_no_test_dataset(self, fit):
        model, dataset_loader_train, model_persister = Mock(), Mock(), Mock()
        X, y = object(), object()
        dataset_loader_train.return_value = X, y

        result = fit(dataset_loader_train, model, model_persister,
                     evaluate=True)

        assert result is model
        dataset_loader_train.assert_called_with()
        model.fit.assert_called_with(X, y)
        assert model.score.call_count == 1
        model.score.assert_called_with(X, y)
        model_persister.write.assert_called_with(model)

    def test_evaluate_with_test_dataset(self, fit):
        model, dataset_loader_train, model_persister = Mock(), Mock(), Mock()
        dataset_loader_test = Mock()
        X, y, X_test, y_test = object(), object(), object(), object()
        dataset_loader_train.return_value = X, y
        dataset_loader_test.return_value = X_test, y_test

        result = fit(dataset_loader_train, model, model_persister,
                     dataset_loader_test=dataset_loader_test,
                     evaluate=True)

        assert result is model
        dataset_loader_train.assert_called_with()
        dataset_loader_test.assert_called_with()
        model.fit.assert_called_with(X, y)
        assert model.score.call_count == 2
        assert model.score.mock_calls[0] == call(X, y)
        assert model.score.mock_calls[1] == call(X_test, y_test)
        model_persister.write.assert_called_with(model)

    def test_evaluate_annotations(self, fit, dataset_loader):
        model = Mock()
        model.score.side_effect = [0.9, 0.8]

        result = fit(
            dataset_loader_train=dataset_loader,
            model=model,
            model_persister=Mock(),
            dataset_loader_test=dataset_loader,
            persist_if_better_than=0.9,
            )

        assert result.__metadata__['score_train'] == 0.9
        assert result.__metadata__['score_test'] == 0.8

    def test_persist_if_better_than(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()
        model.score.return_value = 0.9

        result = fit(
            dataset_loader_train=dataset_loader,
            model=model,
            model_persister=model_persister,
            dataset_loader_test=dataset_loader,
            persist_if_better_than=0.9,
            )

        assert result is model
        assert model_persister.write.call_count == 1

    def test_persist_if_better_than_false(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()
        model.score.return_value = 0.9

        result = fit(
            dataset_loader_train=dataset_loader,
            model=model,
            model_persister=model_persister,
            dataset_loader_test=dataset_loader,
            persist_if_better_than=0.91,
            )

        assert result is model
        assert model_persister.write.call_count == 0

    def test_persist_if_better_than_persist_false(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()
        model.score.return_value = 0.9

        result = fit(
            dataset_loader_train=dataset_loader,
            model=model,
            model_persister=model_persister,
            persist=False,
            dataset_loader_test=dataset_loader,
            persist_if_better_than=0.9,
            )

        assert result is model
        assert model_persister.write.call_count == 0

    def test_persist_if_better_than_no_dataset_test(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()
        model.score.return_value = 0.9

        with pytest.raises(ValueError):
            fit(
                dataset_loader_train=dataset_loader,
                model=model,
                model_persister=model_persister,
                dataset_loader_test=None,
                persist_if_better_than=0.9,
                )

    def test_activate_no_persist(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()

        result = fit(
            dataset_loader_train=dataset_loader,
            model=model,
            model_persister=model_persister,
            persist=False,
            )
        assert result is model
        model_persister.activate.call_count == 0

    def test_timestamp(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()

        def persist(model):
            assert 'train_timestamp' in model.__metadata__
        model_persister.write.side_effect = persist

        before_fit = datetime.now()
        result = fit(
            dataset_loader,
            model,
            model_persister,
            )
        after_fit = datetime.now()

        assert result is model

        timestamp = parse(model.__metadata__['train_timestamp'])
        assert before_fit < timestamp < after_fit
        model_persister.write.assert_called_with(model)


def test_activate():
    from palladium.fit import activate

    persister = Mock()
    activate(persister, 2)
    persister.activate.assert_called_with(2)


def test_delete():
    from palladium.fit import delete

    persister = Mock()
    delete(persister, 2)
    persister.delete.assert_called_with(2)


class TestGridSearch:
    @pytest.fixture
    def grid_search(self):
        from palladium.fit import grid_search
        return grid_search

    def test_it(self, grid_search):
        model, dataset_loader_train = Mock(), Mock()
        grid_search_params = {'verbose': 4}
        X, y = object(), object()
        dataset_loader_train.return_value = X, y
        scores = {
            'mean_test_score': [0.1, 0.2],
            'std_test_score': [0.06463643, 0.05073433],
            'params': [{'C': 0.1}, {'C': 0.3}]}

        with patch('palladium.fit.GridSearchCV') as GridSearchCV:
            GridSearchCV().cv_results_ = scores
            result = grid_search(
                dataset_loader_train, model, grid_search_params)

        expected = []
        expected.append("mean: {0:.5f}, std: {1:.5f}, params: {2}"
                        .format(
                            scores['mean_test_score'][0],
                            scores['std_test_score'][0],
                            scores['params'][0]))
        expected.append("mean: {0:.5f}, std: {1:.5f}, params: {2}"
                        .format(
                            scores['mean_test_score'][1],
                            scores['std_test_score'][1],
                            scores['params'][1]))
        assert result == expected
        dataset_loader_train.assert_called_with()
        GridSearchCV.assert_called_with(model, refit=False, verbose=4)
        GridSearchCV().fit.assert_called_with(X, y)

    def test_no_score_method_raises(self, grid_search):
        model, dataset_loader_train = Mock(spec=['fit', 'predict']), Mock()
        dataset_loader_train.return_value = object(), object()

        with pytest.raises(ValueError):
            grid_search(dataset_loader_train, model, {})

    def test_grid_search(self, grid_search):
        model, dataset_loader_train = Mock(), Mock()
        dataset_loader_train.return_value = (
            np.random.random((10, 10)), np.random.random(10))

        CVIterator = Mock()

        def cv_iterator(n, p):
            return CVIterator(n=n, p=p)

        grid_search_params = {'cv': partial(cv_iterator, p=2)}

        scores = {
            'mean_test_score': [0.1, 0.2],
            'std_test_score': [0.06463643, 0.05073433],
            'params': [{'C': 0.1}, {'C': 0.3}]}
        with patch('palladium.fit.GridSearchCV') as GridSearchCV:
            GridSearchCV().cv_results_ = scores
            grid_search(dataset_loader_train, model, grid_search_params)

        GridSearchCV.assert_called_with(model, refit=False,
                                        cv=CVIterator.return_value)
        CVIterator.assert_called_with(n=10, p=2)


class TestFitMode():
    # test if fit mode is set in non-server scripts

    @pytest.mark.parametrize("func, cmd, argv", [
        ('palladium.fit.fit', 'palladium.fit.fit_cmd', ()),
        ('palladium.fit.grid_search', 'palladium.fit.grid_search_cmd', ()),
        ('palladium.fit.activate', 'palladium.fit.admin_cmd',
         ('activate', '1')),
        ('palladium.eval.test', 'palladium.eval.test_cmd', ()),
        ('palladium.eval.list', 'palladium.eval.list_cmd', ()),
        ('palladium.util.upgrade', 'palladium.util.upgrade_cmd', ()),
        ])
    def test_check_fit_mode(self, func, cmd, argv, config):
        from palladium.util import resolve_dotted_name
        with patch(func):
            cmd = resolve_dotted_name(cmd)
            assert config.initialized is False
            cmd(argv=argv)
            assert config.initialized is True
            assert config == {'__mode__': 'fit'}
