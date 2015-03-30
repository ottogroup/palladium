from datetime import datetime
import json
from unittest.mock import Mock
from unittest.mock import patch

import dateutil.parser
from flask import request
import numpy as np
import pytest
from werkzeug.exceptions import BadRequest


class TestPredictService:
    @pytest.fixture
    def PredictService(self):
        from palladium.server import PredictService
        return PredictService

    def test_functional(self, PredictService, flask_app):
        model = Mock()
        model.threshold = 0.3
        model.size = 10
        # needed as hasattr would evaluate to True otherwise
        del model.threshold2
        del model.size2
        model.predict.return_value = np.array(['class1'])
        service = PredictService(
            mapping=[
                ('sepal length', 'float'),
                ('sepal width', 'float'),
                ('petal length', 'float'),
                ('petal width', 'float'),
                ('color', 'str'),
                ('age', 'int'),
                ('active', 'bool'),
                ('austrian', 'bool'),
                ],
            params=[
                ('threshold', 'float'),  # default will be overwritten
                ('size', 'int'),  # not provided, default value kept
                ('threshold2', 'float'),  # will be used, no default value
                ('size2', 'int'),  # not provided, no default value
                ])

        with flask_app.test_request_context():
            with patch('palladium.util.get_config') as get_config:
                meta_dict = {
                    'service_metadata': {
                        'service_name': 'iris',
                        'service_version': '0.1'
                    }
                }
                get_config.return_value = meta_dict
                resp = service(
                    model,
                    Mock(args=dict([
                        ('sepal length', '5.2'),
                        ('sepal width', '3.5'),
                        ('petal length', '1.5'),
                        ('petal width', '0.2'),
                        ('color', 'purple'),
                        ('age', '1'),
                        ('active', 'True'),
                        ('austrian', 'False'),
                        ('threshold', '0.7'),
                        ('threshold2', '0.8'),
                    ]))
                )

        assert (model.predict.call_args[0][0] ==
                np.array([[5.2, 3.5, 1.5, 0.2,
                           'purple', 1, True, False]], dtype='object')).all()
        assert model.predict.call_args[1]['threshold'] == 0.7
        assert model.predict.call_args[1]['size'] == 10
        assert model.predict.call_args[1]['threshold2'] == 0.8
        assert 'size2' not in model.predict.call_args[1]
        assert resp.status_code == 200
        expected_resp_data = {
            "metadata": {
                "status": "OK",
                "error_code": 0,
                "service_name": "iris",
                "service_version": "0.1",
                },
            "result": "class1"
            }

        assert json.loads(resp.get_data(as_text=True)) == expected_resp_data

    def test_bad_request(self, PredictService, flask_app):
        predict_service = PredictService(mapping=[])
        model = Mock()
        request = Mock()
        with patch.object(predict_service, 'do') as psd:
            with flask_app.test_request_context():
                with patch('palladium.util.get_config') as get_config:
                    meta_dict = {
                        'service_metadata': {}
                    }
                    get_config.return_value = meta_dict
                    bad_request = BadRequest()
                    bad_request.args = ('daniel',)
                    psd.side_effect = bad_request
                    resp = predict_service(model, request)
        resp_data = json.loads(resp.get_data(as_text=True))
        assert resp.status_code == 400
        assert resp_data == {
            "metadata": {
                "status": "ERROR",
                "error_code": -1,
                "error_message": "BadRequest: ('daniel',)"
                }
            }

    def test_predict_error(self, PredictService, flask_app):
        from palladium.interfaces import PredictError
        predict_service = PredictService(mapping=[])
        model = Mock()
        request = Mock()
        with patch.object(predict_service, 'do') as psd:
            with flask_app.test_request_context():
                with patch('palladium.util.get_config') as get_config:
                    meta_dict = {
                        'service_metadata': {}
                    }
                    get_config.return_value = meta_dict
                    psd.side_effect = PredictError("mymessage", 123)
                    resp = predict_service(model, request)
        resp_data = json.loads(resp.get_data(as_text=True))
        assert resp.status_code == 500
        assert resp_data == {
            "metadata": {
                "status": "ERROR",
                "error_code": 123,
                "error_message": "mymessage",
                }
            }

    def test_generic_error(self, PredictService, flask_app):
        predict_service = PredictService(mapping=[])
        model = Mock()
        request = Mock()
        with patch.object(predict_service, 'do') as psd:
            with flask_app.test_request_context():
                with patch('palladium.util.get_config') as get_config:
                    meta_dict = {
                        'service_metadata': {}
                    }
                    get_config.return_value = meta_dict
                    psd.side_effect = KeyError("model")
                    resp = predict_service(model, request)
        resp_data = json.loads(resp.get_data(as_text=True))
        assert resp.status_code == 500
        assert resp_data == {
            "metadata": {
                "status": "ERROR",
                "error_code": -1,
                "error_message": "KeyError: 'model'",
                }
            }

    def test_sample_from_request(self, PredictService):
        predict_service = PredictService(
            mapping=[
                ('name', 'str'),
                ('sepal width', 'int'),
                ],
            )

        model = Mock()
        request = Mock(args={'name': 'myflower', 'sepal width': 3})
        sample, params = predict_service.sample_from_request(model, request)
        assert sample[0][0] == 'myflower'
        assert sample[0][1] == 3

    def test_probas(self, PredictService, flask_app):
        model = Mock()
        model.predict_proba.return_value = np.array([[0.1, 0.5, 0.4]])
        predict_service = PredictService(mapping=[], predict_proba=True)
        with flask_app.test_request_context():
            with patch('palladium.util.get_config') as get_config:
                meta_dict = {
                    'service_metadata': {}
                }
                get_config.return_value = meta_dict
                resp = predict_service(model, request)
        resp_data = json.loads(resp.get_data(as_text=True))
        assert resp.status_code == 200
        assert resp_data == {
            "metadata": {
                "status": "OK",
                "error_code": 0,
                },
            "result": [0.1, 0.5, 0.4],
            }


class TestPredict:
    @pytest.fixture
    def predict(self):
        from palladium.server import predict
        return predict

    def test_predict_functional(self, config, flask_app, flask_client):
        from palladium.server import make_ujson_response
        model_persister = config['model_persister'] = Mock()
        predict_service = config['predict_service'] = Mock()
        with flask_app.test_request_context():
            predict_service.return_value = make_ujson_response(
                'a', status_code=200)

        model = model_persister.read()

        resp = flask_client.get(
            'predict?sepal length=1.0&sepal width=1.1&'
            'petal length=0.777&petal width=5')

        resp_data = json.loads(resp.get_data(as_text=True))

        assert resp_data == 'a'
        assert resp.status_code == 200
        with flask_app.test_request_context():
            predict_service.assert_called_with(model, request)

    def test_unknown_exception(self, predict, flask_app):
        model_persister = Mock()
        model_persister.read.side_effect = KeyError('model')

        with flask_app.test_request_context():
            resp = predict(model_persister, Mock())
        resp_data = json.loads(resp.get_data(as_text=True))
        assert resp.status_code == 500
        assert resp_data == {
            "status": "ERROR",
            "error_code": -1,
            "error_message": "KeyError: 'model'",
            }


class TestAliveFunctional:
    def test_empty_process_state(self, config, flask_client):
        config['service_metadata'] = {'hello': 'world'}
        resp = flask_client.get('alive')
        assert resp.status_code == 200
        resp_data = json.loads(resp.get_data(as_text=True))

        assert sorted(resp_data.keys()) == ['memory_usage',
                                            'palladium_version',
                                            'service_metadata']
        assert resp_data['service_metadata'] == config['service_metadata']

    def test_filled_process_state(self, config, process_store, flask_client):
        config['alive'] = {'process_store_required': ('model', 'data')}

        before = datetime.now()
        process_store['model'] = Mock(__metadata__={'hello': 'is it me'})
        process_store['data'] = Mock(__metadata__={'bye': 'not you'})
        after = datetime.now()

        resp = flask_client.get('alive')
        assert resp.status_code == 200
        resp_data = json.loads(resp.get_data(as_text=True))

        model_updated = dateutil.parser.parse(resp_data['model']['updated'])
        data_updated = dateutil.parser.parse(resp_data['data']['updated'])
        assert before < model_updated < after
        assert resp_data['model']['metadata'] == {'hello': 'is it me'}
        assert before < data_updated < after
        assert resp_data['data']['metadata'] == {'bye': 'not you'}

    def test_missing_process_state(self, config, process_store, flask_client):
        config['alive'] = {'process_store_required': ('model', 'data')}
        process_store['model'] = Mock(__metadata__={'hello': 'is it me'})

        resp = flask_client.get('alive')
        assert resp.status_code == 503
        resp_data = json.loads(resp.get_data(as_text=True))

        assert resp_data['model']['metadata'] == {'hello': 'is it me'}
        assert resp_data['data'] == 'N/A'
