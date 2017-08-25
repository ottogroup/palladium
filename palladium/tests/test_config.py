import pytest
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import mock_open
from unittest.mock import patch


class MyDummyComponent:
    def __init__(self, arg1, arg2='blargh', subcomponent=None):
        self.arg1 = arg1
        self.arg2 = arg2
        self.subcomponent = subcomponent
        self.initialize_component_arg = None

    def initialize_component(self, config):
        self.initialize_component_arg = config


def test_create_component():
    from palladium.config import create_component

    result = create_component({
        '__factory__': 'palladium.tests.test_config.MyDummyComponent',
        'arg1': 3,
        })
    assert isinstance(result, MyDummyComponent)
    assert result.arg1 == 3
    assert result.arg2 == 'blargh'


def test_config_class_keyerror():
    from palladium.config import Config
    with pytest.raises(KeyError) as e:
        Config({})['invalid']
    assert "Maybe you forgot to set" in str(e.value)


class TestInitializeConfigImpl:
    @pytest.fixture
    def _initialize_config(self):
        from palladium.config import _initialize_config
        return _initialize_config

    def test_initialize_config(self, _initialize_config):
        dummy = 'palladium.tests.test_config.MyDummyComponent'
        config = {
            'mycomponent': {
                '__factory__': dummy,
                'arg1': 3,
                'arg2': {'no': 'factory'},
                'subcomponent': {
                    '__factory__': dummy,
                    'arg1': {
                        'subsubcomponent': {
                            '__factory__':
                            dummy,
                            'arg1': 'wobwob',
                            'arg2': 9,
                            },
                        },
                    'arg2': 6,
                    },
                },
            'mylistofcomponents': [{
                '__factory__': dummy,
                'arg1': 'wobwob',
                },
                'somethingelse',
                ],
            'mynestedlistofcomponents': [[{
                '__factory__': dummy,
                'arg1': 'feep',
                'arg2': {
                    '__factory__': dummy,
                    'arg1': 6,
                },
            }]],
            'myconstant': 42,
            }

        config = _initialize_config(config)
        assert config['myconstant'] == 42

        mycomponent = config['mycomponent']
        assert isinstance(mycomponent, MyDummyComponent)
        assert mycomponent.arg1 == 3
        assert mycomponent.arg2 == {'no': 'factory'}
        assert mycomponent.initialize_component_arg is config

        subcomponent = mycomponent.subcomponent
        assert isinstance(subcomponent, MyDummyComponent)
        assert subcomponent.arg2 == 6
        assert subcomponent.initialize_component_arg is config

        subsubcomponent = subcomponent.arg1['subsubcomponent']
        assert isinstance(subsubcomponent, MyDummyComponent)
        assert subsubcomponent.arg1 == 'wobwob'
        assert subsubcomponent.arg2 == 9
        assert subsubcomponent.initialize_component_arg is config

        mylistofcomponents = config['mylistofcomponents']
        assert len(mylistofcomponents) == 2
        assert isinstance(mylistofcomponents[0], MyDummyComponent)
        assert mylistofcomponents[0].arg1 == 'wobwob'
        assert mylistofcomponents[1] == 'somethingelse'

        mnl = config['mynestedlistofcomponents']
        assert isinstance(mnl[0][0], MyDummyComponent)
        assert mnl[0][0].arg1 == 'feep'
        assert isinstance(mnl[0][0].arg2, MyDummyComponent)

    def test_initialize_config_logging(self, _initialize_config):
        with patch('palladium.config.dictConfig') as dictConfig:
            _initialize_config({'logging': 'yes, please'})
            dictConfig.assert_called_with('yes, please')


class TestInitializeConfig:
    @pytest.fixture
    def initialize_config(self):
        from palladium.config import initialize_config
        return initialize_config

    def test_initialize_config_extra(self, config,
                                     initialize_config):
        config.clear()
        initialize_config(two='three')
        assert config['two'] == 'three'

    def test_initialize_config_already_initialized(self, config,
                                                   initialize_config):
        config.clear()
        config.initialized = True
        with pytest.raises(RuntimeError):
            initialize_config(two='three')


class TestGetConfig:
    @pytest.fixture
    def get_config(self):
        from palladium.config import get_config
        return get_config

    def test_read(self, get_config, config):
        config.initialized = False
        config_in = {
            'mycomponent': {
                '__factory__': 'palladium.tests.test_config.MyDummyComponent',
                'arg1': 3,
                },
            'myconstant': 42,
            }

        with patch('palladium.config.open',
                   mock_open(read_data=str(config_in)),
                   create=True):
            with patch('palladium.config.os.environ', {'PALLADIUM_CONFIG': 'somepath'}):
                config_new = get_config()

            assert config_new['myconstant'] == config_in['myconstant']
            mycomponent = config_new['mycomponent']
            assert isinstance(mycomponent, MyDummyComponent)
            assert mycomponent.arg1 == 3

    def test_read_multiple_files(self, get_config, config):
        config.initialized = False

        fake_open = MagicMock()
        fake_open.return_value.__enter__.return_value.read.side_effect = [
            "{'a': 42, 'b': 6}", "{'b': 7}"
            ]
        with patch('palladium.config.open', fake_open, create=True):
            with patch('palladium.config.os.environ', {
                'PALLADIUM_CONFIG': 'somepath, andanother',
                    }):
                config_new = get_config()

        assert config_new == {'a': 42, 'b': 7}

        # Files later in the list override files earlier in the list:
        assert fake_open.call_args_list == [
            call('somepath'), call('andanother')]

    def test_read_environ(self, get_config, config):
        config.initialized = False
        config_in_str = """
{
'mycomponent': {
    '__factory__': 'palladium.tests.test_config.MyDummyComponent',
    'arg1': 3,
    'arg2': "{}:{}".format(environ['PALLADIUM_DB_IP'],
                           environ['PALLADIUM_DB_PORT']),
    },
}"""

        with patch('palladium.config.open',
                   mock_open(read_data=config_in_str),
                   create=True):
            with patch('palladium.config.os.environ', {
                    'PALLADIUM_CONFIG': 'somepath',
                    'PALLADIUM_DB_IP': '192.168.0.1',
                    'PALLADIUM_DB_PORT': '666',
            }):
                config_new = get_config()

            mycomponent = config_new['mycomponent']
            assert isinstance(mycomponent, MyDummyComponent)
            assert mycomponent.arg1 == 3
            assert mycomponent.arg2 == '192.168.0.1:666'

    def test_read_here(self, get_config, config):
        config.initialized = False
        config_in_str = "{'here': here}"

        with patch('palladium.config.open',
                   mock_open(read_data=config_in_str),
                   create=True):
            with patch('palladium.config.os.environ', {
                    'PALLADIUM_CONFIG': '/home/megha/somepath.py',
            }):
                config_new = get_config()

            assert config_new['here'] == '/home/megha'
