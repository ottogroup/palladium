from datetime import datetime
from functools import partial
import numpy as np
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

from dateutil.parser import parse
import pandas
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
        del model.cv_results_
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
        del model.cv_results_
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
        del model.cv_results_
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
        del model.cv_results_
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
        del model.cv_results_
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

    def test_evaluate_scoring(self, fit, dataset_loader):
        model = Mock()
        del model.cv_results_
        scorer = Mock()
        scorer.side_effect = [0.99, 0.01]

        fit(
            dataset_loader_train=dataset_loader,
            model=model,
            model_persister=Mock(),
            dataset_loader_test=dataset_loader,
            scoring=scorer,
            evaluate=True,
            )
        assert model.score.call_count == 0
        assert scorer.call_count == 2

    def test_evaluate_no_score(self, fit, dataset_loader):
        model = Mock()
        del model.score
        del model.cv_results_

        with pytest.raises(ValueError):
            fit(
                dataset_loader_train=dataset_loader,
                model=model,
                model_persister=Mock(),
                dataset_loader_test=dataset_loader,
                evaluate=True,
                )

    def test_persist_if_better_than(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()
        model.score.return_value = 0.9
        del model.cv_results_

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
        del model.cv_results_

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
        del model.cv_results_

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
        del model.cv_results_

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
        del model.cv_results_

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
        del model.cv_results_

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

    def test_cv_results(self, fit, dataset_loader):
        model, model_persister = Mock(), Mock()
        model.cv_results_ = {
            'mean_train_score': [3, 2, 1],
            'mean_test_score': [1, 2, 3],
            }

        def persist(model):
            assert 'cv_results' in model.__metadata__

        model_persister.write.side_effect = persist

        result = fit(
            dataset_loader,
            model,
            model_persister,
            )
        assert result is model

        cv_results = model.__metadata__['cv_results']
        cv_results = pandas.read_json(cv_results).to_dict(orient='list')
        assert cv_results == model.cv_results_
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
    def GridSearchCVWithScores(self, monkeypatch):
        scores = {
            'mean_test_score': [0.1, 0.2],
            'std_test_score': [0.06463643, 0.05073433],
            'params': [{'C': 0.1}, {'C': 0.3}],
            'rank_test_score': [1, 2],
            }

        GridSearchCV = Mock()
        monkeypatch.setattr('palladium.fit.GridSearchCV', GridSearchCV)
        GridSearchCV().cv_results_ = scores
        return GridSearchCV

    @pytest.fixture
    def grid_search(self):
        from palladium.fit import grid_search
        return grid_search

    def test_it(self, grid_search, GridSearchCVWithScores, capsys, tmpdir):
        model, dataset_loader_train = Mock(), Mock()
        grid_search_params = {'verbose': 4}
        X, y = object(), object()
        dataset_loader_train.return_value = X, y

        results_csv = tmpdir.join('results.csv')
        result = grid_search(
            dataset_loader_train=dataset_loader_train,
            model=model,
            grid_search=grid_search_params,
            save_results=str(results_csv),
            )
        dataset_loader_train.assert_called_with()
        GridSearchCVWithScores.assert_called_with(model, refit=False, verbose=4)
        GridSearchCVWithScores().fit.assert_called_with(X, y)
        assert result is GridSearchCVWithScores()
        scores = GridSearchCVWithScores().cv_results_
        assert (str(pandas.DataFrame(scores)).strip() ==
                capsys.readouterr()[0].strip())
        assert (str(pandas.DataFrame(scores)).strip() ==
                str(pandas.read_csv(str(results_csv))).strip())

    def test_no_score_method_raises(self, grid_search):
        model, dataset_loader_train = Mock(spec=['fit', 'predict']), Mock()
        dataset_loader_train.return_value = object(), object()

        with pytest.raises(ValueError):
            grid_search(dataset_loader_train, model, {})

    def test_two_scores_raises(self, grid_search):
        model, dataset_loader_train = Mock(spec=['fit', 'predict']), Mock()
        dataset_loader_train.return_value = object(), object()

        with pytest.raises(ValueError):
            grid_search(dataset_loader_train, model,
                        {'scoring': 'f1'}, scoring='accuracy')

    def test_two_scores_priority(self, grid_search, GridSearchCVWithScores):
        # 'scoring' has higher priority than 'model.score'
        model = Mock(spec=['fit', 'predict', 'score'])
        dataset_loader_train = Mock()
        scoring = Mock()
        dataset_loader_train.return_value = object(), object()

        grid_search(dataset_loader_train, model, {}, scoring=scoring)
        GridSearchCVWithScores.assert_called_with(
            model, refit=False, scoring=scoring)

    def test_deprecated_scoring(self, grid_search, GridSearchCVWithScores):
        # 'scoring' inside of 'grid_search' is deprecated
        model = Mock(spec=['fit', 'predict', 'score'])
        dataset_loader_train = Mock()
        scoring = Mock()
        dataset_loader_train.return_value = object(), object()

        with pytest.warns(DeprecationWarning):
            grid_search(dataset_loader_train, model,
                        {'scoring': scoring}, scoring=None)
        GridSearchCVWithScores.assert_called_with(
            model, refit=False, scoring=scoring)

    def test_persist_best_requires_persister(self, grid_search):
        model = Mock(spec=['fit', 'predict'])
        del model.cv_results_
        dataset_loader_train = Mock()
        scoring = Mock()
        dataset_loader_train.return_value = object(), object()

        with pytest.raises(ValueError):
            grid_search(dataset_loader_train, model, {}, scoring=scoring,
                        persist_best=True)

    def test_persist_best(self, grid_search, GridSearchCVWithScores):
        model = Mock(spec=['fit', 'predict'])
        del model.cv_results_
        dataset_loader_train = Mock()
        scoring = Mock()
        model_persister = Mock()
        dataset_loader_train.return_value = object(), object()

        grid_search(dataset_loader_train, model, {}, scoring=scoring,
                    persist_best=True, model_persister=model_persister)
        GridSearchCVWithScores.assert_called_with(
            model, refit=True, scoring=scoring)
        model_persister.write.assert_called_with(
            GridSearchCVWithScores())

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
