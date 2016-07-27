class TestWsgi:
    def test_module_loads_config(self, config):
        assert config.initialized is False
        from palladium import wsgi  # initializes config
        # fit mode should only be set by non-server scripts
        assert config.get('__mode__') is None
        assert config.initialized is True
