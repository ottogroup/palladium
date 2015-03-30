from unittest.mock import MagicMock

import pytest


class TestAnnotate:
    @pytest.fixture
    def annotate(self):
        from palladium.interfaces import annotate
        return annotate

    def test_with_existing_data(self, annotate):
        model = MagicMock(__metadata__={'one': 1, 'two': 2})
        annotate(model, {'one': '11'})
        assert model.__metadata__['one'] == '11'
        assert model.__metadata__['two'] == 2
        assert annotate(model) == {'one': '11', 'two': 2}

    def test_without_existing_data(self, annotate):
        model = TestAnnotate()
        assert annotate(model, {'one': '11'}) == {'one': '11'}
        assert model.__metadata__['one'] == '11'


class TestPredictError:
    @pytest.fixture
    def PredictError(self):
        from palladium.interfaces import PredictError
        return PredictError

    def test_str(self, PredictError):
        assert str(PredictError("message", 123)) == "message (123)"
