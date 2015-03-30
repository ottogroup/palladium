from unittest.mock import call
from unittest.mock import Mock
from unittest.mock import patch

import numpy as np
import pytest
from pytest import fixture


pytest.importorskip("julia")


@fixture
def bridge(monkeypatch):
    make_bridge = Mock()
    monkeypatch.setattr('palladium.julia.make_bridge', make_bridge)
    return make_bridge.return_value


class TestAbstractModel:
    @fixture
    def Model(self):
        from palladium.julia import AbstractModel
        return AbstractModel

    @fixture
    def model(self, Model, bridge):
        return Model(
            fit_func='myjulia.fit_func',
            predict_func='yourjulia.predict_func',
            fit_kwargs={'fit': 'kwargs'},
            predict_kwargs={'predict': 'kwargs'},
            )

    def test_initialize_julia(self, model, bridge):
        bridge.eval.side_effect = ['fit', 'predict']
        model._initialize_julia()
        assert model.fit_func_ == 'fit'
        assert model.predict_func_ == 'predict'

        assert call('import myjulia') in bridge.mock_calls
        assert call('import yourjulia') in bridge.mock_calls
        assert call('myjulia.fit_func') in bridge.mock_calls
        assert call('yourjulia.predict_func') in bridge.mock_calls

    def test_fit(self, model):
        X, y = Mock(), Mock()
        assert model.fit(X, y) is model
        fit_func = model.fit_func_
        fit_func.assert_called_with(X.T, y, fit='kwargs')
        assert model.fitted_ == fit_func.return_value

    def test_fit_with_label_encoder(self, model):
        model.encode_labels = True
        X, y = Mock(), Mock()
        with patch('palladium.julia.LabelEncoder') as encoder:
            model.fit(X, y) is model
        fit_func = model.fit_func_
        transform = encoder().fit_transform
        fit_func.assert_called_with(X.T, transform.return_value, fit='kwargs')

    def test_predict(self, model):
        X = Mock()
        model.fitted_ = Mock()
        model._initialize_julia()
        result = model.predict(X)
        predict_func = model.predict_func_
        predict_func.assert_called_with(
            model.fitted_, X.astype().T, predict='kwargs')
        assert result == predict_func.return_value

    def test_predict_with_label_encoder(self, model):
        model.encode_labels = True
        X = Mock()
        model.fitted_ = Mock()
        model.enc_ = Mock()
        inverse_transform = model.enc_.inverse_transform
        model._initialize_julia()
        result = model.predict(X)
        assert result == inverse_transform.return_value
        inverse_transform.assert_called_with(model.predict_func_.return_value)

    def test_predict_convert_to_float(self, model):
        X_in = np.array([1, 2, 3], dtype=object)
        model.fitted_ = Mock()
        model.enc_ = Mock()
        model._initialize_julia()
        model.predict(X_in)
        X_conv = model.predict_func_.call_args[0][1]
        assert np.all(X_in == X_conv)
        assert X_conv.dtype == np.float64

    def test_getstate(self, model):
        model._initialize_julia()
        model.fitted_ = Mock()

        state = model.__getstate__()
        assert state['fitted_'] is not model.fitted_
        assert 'fit_func_' not in state
        assert 'predict_func_' not in state
        assert 'bridge_' not in state

        idict = model.__dict__
        assert 'fit_func_' in idict
        assert 'predict_func_' in idict
        assert 'bridge_' in idict

    def test_setstate(self, model, bridge):
        model.__setstate__(
            {'fitted_': 'fitted', 'fit_kwargs': {'bl': 'arg'}})
        assert model.fitted_ != 'fitted'
        assert model.fitted_ == bridge.eval.return_value.return_value


class TestClassificationModel(TestAbstractModel):
    @fixture
    def Model(self):
        from palladium.julia import ClassificationModel
        return ClassificationModel

    def test_score(self, model):
        X, y = Mock(), Mock()
        with patch('palladium.julia.accuracy_score') as accuracy_score:
            with patch('palladium.julia.AbstractModel.predict') as predict:
                model.score(X, y)
        accuracy_score.assert_called_with(predict.return_value, y)
        predict.assert_called_with(X)
