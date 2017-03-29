class TestWsgi:
    def test_module_loads_config(self, flask_app_test, config):
        assert config.initialized is False
        # needed to avoid config postprocessing side effects in this test
        with flask_app_test.test_request_context():
            from palladium import wsgi  # initializes config

        # fit mode should only be set by non-server scripts
        assert config.get('__mode__') is None
        assert config.initialized is True
