import os
import readline  # https://github.com/ContinuumIO/anaconda-issues/issues/152
from unittest.mock import MagicMock
from unittest.mock import Mock

import numpy
from pandas import DataFrame
from pandas import Series
from sklearn.pipeline import Pipeline

import pytest


pytest.importorskip("rpy2")
from rpy2.robjects.pandas2ri import py2ri
from rpy2.robjects.pandas2ri import ri2py
from rpy2.robjects.vectors import Vector


@pytest.fixture
def ObjectMixin(monkeypatch):
    from palladium.R import ObjectMixin
    r_dict = {}
    r = MagicMock()
    r.__getitem__.side_effect = r_dict.__getitem__
    r.__setitem__.side_effect = r_dict.__setitem__
    r['myfunc'] = Mock()
    r['predict'] = Mock()
    monkeypatch.setattr(ObjectMixin, 'r', r)
    return ObjectMixin


class TestDatasetLoader:
    @pytest.fixture
    def DatasetLoader(self, ObjectMixin):
        from palladium.R import DatasetLoader
        return DatasetLoader

    def test_it(self, DatasetLoader):
        X, y = object(), object()
        DatasetLoader.r['myfunc'].return_value = X, y
        dloader = DatasetLoader('myscript', 'myfunc', some='kwarg')
        assert dloader() == (X, y)
        dloader.r.source.assert_called_with('myscript')
        dloader.r['myfunc'].assert_called_with(some='kwarg')


class TestAbstractModel:
    @pytest.fixture
    def data(self):
        X = numpy.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        y = numpy.array([1, 2])
        return X, y

    @pytest.fixture
    def dataframe(self, data):
        X, y = data
        return DataFrame(X, columns=['one', 'two', 'three']), Series(y)

    @pytest.fixture
    def Model(self, ObjectMixin, monkeypatch):
        from palladium.R import AbstractModel
        monkeypatch.setattr(AbstractModel, '__abstractmethods__', set())
        return AbstractModel

    def test_fit_with_numpy_data(self, Model, data):
        X, y = data
        model = Model(scriptname='myscript', funcname='myfunc', some='kwarg')
        model.fit(X, y)
        funcargs = model.r['myfunc'].call_args
        assert (numpy.asarray(funcargs[0][0]) == X).all()
        assert (numpy.asarray(funcargs[0][1]) == y).all()
        assert funcargs[1]['some'] == 'kwarg'

    def test_fit_with_pandas_data(self, Model, dataframe):
        X, y = dataframe
        model = Model(scriptname='myscript', funcname='myfunc', some='kwarg')
        model.fit(X, y)
        funcargs = model.r['myfunc'].call_args
        assert (ri2py(funcargs[0][0]).values == X.values).all()
        assert (ri2py(funcargs[0][1]) == y).all()
        assert funcargs[1]['some'] == 'kwarg'


class TestClassificationModel(TestAbstractModel):
    @pytest.fixture
    def Model(self, ObjectMixin, monkeypatch):
        from palladium.R import ClassificationModel
        return ClassificationModel

    def test_predict_with_numpy_data(self, Model, data):
        X, y = data
        model = Model(scriptname='myscript', funcname='myfunc', some='kwarg')
        model.r['predict'].return_value = numpy.array(
            [[0.1, 0.2, 0.7], [0.8, 0.1, 0.1]])
        model.fit(X, y)

        result = model.predict(X)
        predictargs = model.r['predict'].call_args
        assert predictargs[0][0] is model.rmodel_
        assert (numpy.asarray(predictargs[0][1]) == X).all()
        assert predictargs[1]['type'] == 'prob'
        assert (result ==
                numpy.argmax(model.r['predict'].return_value, axis=1)).all()

        result = model.predict_proba(X)
        assert (result == model.r['predict'].return_value).all()

    def test_predict_with_pandas_data(self, Model, dataframe):
        X, y = dataframe
        model = Model(scriptname='myscript', funcname='myfunc', some='kwarg')
        model.r['predict'].return_value = numpy.array(
            [[0.1, 0.2, 0.7], [0.8, 0.1, 0.1]])
        model.fit(X, y)

        result = model.predict(X)
        predictargs = model.r['predict'].call_args
        assert predictargs[0][0] is model.rmodel_
        assert (ri2py(predictargs[0][1]).values == X.values).all()
        assert predictargs[1]['type'] == 'prob'
        assert (result ==
                numpy.argmax(model.r['predict'].return_value, axis=1)).all()

        result = model.predict_proba(X)
        assert (result == model.r['predict'].return_value).all()


class TestClassification:
    @pytest.fixture
    def dataset(self):
        from palladium.R import DatasetLoader
        return DatasetLoader(
            scriptname=os.path.join(os.path.dirname(__file__), 'test_R.R'),
            funcname='dataset',
            )

    @pytest.fixture
    def model(self):
        from palladium.R import ClassificationModel
        return ClassificationModel(
            scriptname=os.path.join(os.path.dirname(__file__), 'test_R.R'),
            funcname='train.randomForest',
            encode_labels=True,
            )

    def test_fit_and_predict(self, dataset, model):
        X, y = dataset()
        model.fit(X, y)
        probas = model.predict_proba(X)
        assert probas.shape == (150, 3)
        assert (probas.sum(axis=1) == 1).all()
        assert (model.predict(X) == numpy.asarray(y)).all()

    def test_fit_and_score(self, dataset, model):
        X, y = dataset()
        model.fit(X, y)
        assert model.score(X, y) == 1.0


class TestClassificationWithNumpyDataset(TestClassification):
    @pytest.fixture
    def dataset(self):
        X = numpy.array([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
            ] * 50)
        y = numpy.array([1, 2, 3] * 50)
        return lambda: (X, y)


class TestClassificationWithPandasDataset(TestClassification):
    @pytest.fixture
    def dataset(self):
        X = DataFrame([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
            ] * 50)
        y = Series([1, 2, 3] * 50)
        return lambda: (X, y)


class TestRegression:
    @pytest.fixture
    def scriptname(self):
        return os.path.join(os.path.dirname(__file__), 'test_R2.R')

    @pytest.fixture
    def dataset(self, scriptname):
        from palladium.R import DatasetLoader
        return DatasetLoader(
            scriptname=scriptname,
            funcname='dataset',
            )

    @pytest.fixture
    def model(self, scriptname):
        from palladium.R import RegressionModel
        from palladium.R import Rpy2Transform

        return Pipeline([
            ('rpy2', Rpy2Transform()),
            ('regressor', RegressionModel(
                scriptname=scriptname,
                funcname='train.randomForest',
                )),
            ])

    def test_smoke(self, dataset, model):
        X, y = dataset()
        model.fit(X, y)

        assert model.predict(X).shape == (
            ri2py(y).shape if isinstance(y, Vector) else y.shape)
        score_1 = model.score(X, y)
        assert score_1 >= 0.1

        # Convert X to its Python or R equivalent and check if scores
        # match:
        X_t = py2ri(X) if isinstance(X, DataFrame) else ri2py(X)
        score_2 = model.score(X_t, y)
        assert score_2 == score_1

        # Convert X to a Python list and run the prediction:
        X_t2 = ri2py(X) if not isinstance(X, DataFrame) else X
        X_t2 = X_t2.values.tolist()
        score_3 = model.score(X_t2, y)
        assert score_3 == score_1


class TestRegressionWithPandasDataset(TestRegression):
    @pytest.fixture
    def dataset(self):
        X = DataFrame(
            [
                [1.0, 2.0, 0],
                [4.0, 5.0, 1],
                [7.0, 8.0, 2],
            ] * 50,
            columns=('one', 'two', 'really'),
            )
        X['really'] = X['really'].astype('category')
        y = Series([1.0, 2.0, 3.0] * 50)
        return lambda: (X, y)

    def test_fit_and_predict(self, dataset, model):
        X, y = dataset()
        model.fit(X, y)
        assert (model.predict(X) == numpy.asarray(y)).all()

    def test_fit_and_score(self, dataset, model):
        X, y = dataset()
        model.fit(X, y)
        assert model.score(X, y) == 1.0
