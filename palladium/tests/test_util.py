from datetime import datetime
from time import sleep
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

from dateutil import rrule
import pytest


class MyDummyComponent:
    def __init__(self, arg1, arg2='blargh', subcomponent=None):
        self.arg1 = arg1
        self.arg2 = arg2
        self.subcomponent = subcomponent
        self.initialize_component_arg = None

    def initialize_component(self, config):
        self.initialize_component_arg = config


def test_create_component():
    from palladium.util import create_component

    result = create_component({
        '__factory__': 'palladium.tests.test_util.MyDummyComponent',
        'arg1': 3,
        })
    assert isinstance(result, MyDummyComponent)
    assert result.arg1 == 3
    assert result.arg2 == 'blargh'


def test_config_class_keyerror():
    from palladium.util import Config
    with pytest.raises(KeyError) as e:
        Config({})['invalid']
    assert "Maybe you forgot to set" in str(e.value)


class TestResolveDottedName:
    @pytest.fixture
    def resolve_dotted_name(self):
        from palladium.util import resolve_dotted_name
        return resolve_dotted_name

    def test_with_colon(self, resolve_dotted_name):
        dotted = 'palladium.tests.test_util:TestResolveDottedName.test_with_colon'
        assert (resolve_dotted_name(dotted) is
                TestResolveDottedName.test_with_colon)

    def test_with_dots(self, resolve_dotted_name):
        dotted = 'palladium.tests.test_util.TestResolveDottedName'
        assert (resolve_dotted_name(dotted) is
                TestResolveDottedName)


class TestInitializeConfigImpl:
    @pytest.fixture
    def _initialize_config(self):
        from palladium.util import _initialize_config
        return _initialize_config

    def test_initialize_config(self, _initialize_config):
        config = {
            'mycomponent': {
                '__factory__': 'palladium.tests.test_util.MyDummyComponent',
                'arg1': 3,
                'arg2': {'no': 'factory'},
                'subcomponent': {
                    '__factory__': 'palladium.tests.test_util.MyDummyComponent',
                    'arg1': {
                        'subsubcomponent': {
                            '__factory__':
                            'palladium.tests.test_util.MyDummyComponent',
                            'arg1': 'wobwob',
                            'arg2': 9,
                            },
                        },
                    'arg2': 6,
                    },
                },
            'mylistofcomponents': [{
                '__factory__': 'palladium.tests.test_util.MyDummyComponent',
                'arg1': 'wobwob',
                },
                'somethingelse',
                ],
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

    def test_initialize_config_logging(self, _initialize_config):
        with patch('palladium.util.dictConfig') as dictConfig:
            _initialize_config({'logging': 'yes, please'})
            dictConfig.assert_called_with('yes, please')


class TestInitializeConfig:
    @pytest.fixture
    def initialize_config(self):
        from palladium.util import initialize_config
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
        from palladium.util import get_config
        return get_config

    def test_read(self, get_config, config):
        config.initialized = False
        config_in = {
            'mycomponent': {
                '__factory__': 'palladium.tests.test_util.MyDummyComponent',
                'arg1': 3,
                },
            'myconstant': 42,
            }

        with patch('palladium.util.open',
                   mock_open(read_data=str(config_in)),
                   create=True):
            with patch('palladium.util.os.environ', {'PALLADIUM_CONFIG': 'somepath'}):
                config_new = get_config()

            assert config_new['myconstant'] == config_in['myconstant']
            mycomponent = config_new['mycomponent']
            assert isinstance(mycomponent, MyDummyComponent)
            assert mycomponent.arg1 == 3

    def test_read_environ(self, get_config, config):
        config.initialized = False
        config_in_str = """
{
'mycomponent': {
    '__factory__': 'palladium.tests.test_util.MyDummyComponent',
    'arg1': 3,
    'arg2': "{}:{}".format(environ['PALLADIUM_DB_IP'],
                           environ['PALLADIUM_DB_PORT']),
    },
}"""

        with patch('palladium.util.open',
                   mock_open(read_data=config_in_str),
                   create=True):
            with patch('palladium.util.os.environ', {
                    'PALLADIUM_CONFIG': 'somepath',
                    'PALLADIUM_DB_IP': '192.168.0.1',
                    'PALLADIUM_DB_PORT': '666',
            }):
                config_new = get_config()

            mycomponent = config_new['mycomponent']
            assert isinstance(mycomponent, MyDummyComponent)
            assert mycomponent.arg1 == 3
            assert mycomponent.arg2 == '192.168.0.1:666'


def test_args_from_config(config):
    from palladium.util import args_from_config

    args = []
    config.update({
        'arg1': 'config1',
        'arg2': 'config2',
        'arg4': 'config4',
        })

    @args_from_config
    def myfunc(arg1, arg2, arg3, arg4='default4', arg5='default5'):
        args.append((arg1, arg2, arg3, arg4, arg5))

    myfunc(arg3='myarg3')
    assert args[-1] == ('config1', 'config2', 'myarg3', 'config4', 'default5')

    myfunc(arg2='myarg2', arg3='myarg3', arg5='myarg5')
    assert args[-1] == ('config1', 'myarg2', 'myarg3', 'config4', 'myarg5')

    myfunc('myarg1', arg3='myarg3')
    assert args[-1] == ('myarg1', 'config2', 'myarg3', 'config4', 'default5')

    with pytest.raises(TypeError) as e:
        myfunc()
    assert "Maybe you forgot to set" in str(e.value)


class TestProcessStore:
    @pytest.fixture
    def store(self):
        from palladium.util import ProcessStore
        return ProcessStore()

    def test_get(self, store):
        assert store.get('somekey') is None
        store['somekey'] = '1'
        assert store.get('somekey') == '1'

    def test_getitem(self, store):
        with pytest.raises(KeyError):
            store['somekey']
        store['somekey'] = '1'
        assert store['somekey'] == '1'

    def test_in(self, store):
        assert not 'somekey' in store
        store['somekey'] = '1'
        assert 'somekey' in store

    def test_setitem(self, store):
        store['somekey'] = '1'
        assert store['somekey'] == '1'
        store['somekey'] = '2'
        assert store['somekey'] == '2'

    def test_delitem(self, store):
        store['somekey'] = '1'
        del store['somekey']
        with pytest.raises(KeyError):
            store['somekey']

    def test_mtime_no_entry(self, store):
        with pytest.raises(KeyError):
            assert store.mtime['somekey']

    def test_mtime_setitem(self, store):
        dt0 = datetime.now()
        store['somekey'] = '1'
        dt1 = datetime.now()
        assert dt0 < store.mtime['somekey'] < dt1
        store['somekey'] = '2'
        dt2 = datetime.now()
        assert dt1 < store.mtime['somekey'] < dt2

    def test_mtime_delitem(self, store):
        store['somekey'] = '1'
        del store['somekey']
        with pytest.raises(KeyError):
            store.mtime['somekey']

    def test_init(self, store):
        store = store.__class__({'somekey': '1'})
        assert store['somekey'] == '1'
        assert 'somekey' in store.mtime

    def test_clear(self, store):
        store['somekey'] = '1'
        store.clear()
        assert 'somekey' not in store
        assert 'somekey' not in store.mtime


class TestRruleThread:
    @pytest.fixture
    def RruleThread(self):
        from palladium.util import RruleThread
        return RruleThread

    def test_rrule_from_dict(self, RruleThread):
        func = Mock()
        now = datetime.now()
        rrule_info = {
            'freq': 'DAILY',
            'dtstart': '2014-10-30T13:21:18',
            }
        expected = rrule.rrule(
            rrule.DAILY, dtstart=datetime(2014, 10, 30, 13, 21, 18))

        thread = RruleThread(func, rrule_info)
        assert thread.rrule.after(now) == expected.after(now)

    def test_last_execution(self, RruleThread):
        func = Mock()
        thread = RruleThread(func, rrule.rrule(
            rrule.MONTHLY,
            bymonthday=1,
            dtstart=datetime(2014, 10, 30, 13, 21, 18)))
        thread.last_execution = datetime(2014, 10, 30, 13, 21, 18)
        thread.start()
        sleep(0.005)
        assert func.call_count == 1

    def test_func_raises(self, RruleThread):
        func = Mock(__name__='buggy')
        func.side_effect = KeyError
        thread = RruleThread(func, rrule.rrule(
            rrule.MONTHLY,
            bymonthday=1,
            dtstart=datetime(2014, 10, 30, 13, 21, 18)))
        thread.last_execution = datetime(2014, 10, 30, 13, 21, 18)

        with patch('palladium.util.logger') as logger:
            thread.start()
            sleep(0.005)
            assert func.call_count == 1
            assert logger.exception.call_count == 1

    def test_sleep_between_checks(self, RruleThread):
        func = Mock()
        rr = Mock()
        rr.between.return_value = False
        thread = RruleThread(func, rr, sleep_between_checks=0.0010)
        thread.start()
        sleep(0.005)
        assert func.call_count == 0
        assert rr.between.call_count > 1


def dec1(func):
    def inner(a, b):
        """dec1"""
        return func(a, b) * 10
    return inner


def dec2(func):
    def inner(a, b):
        """dec2"""
        return func(a, b) + 2
    return inner


class TestPluggableDecorator:
    @pytest.fixture
    def PluggableDecorator(self):
        from palladium.util import PluggableDecorator
        return PluggableDecorator

    def test_no_config(self, PluggableDecorator, config):
        decorator = PluggableDecorator('decorator_list')

        @decorator
        def myfunc(a, b):
            """myfunc"""
            return a + b

        result = myfunc(2, 3)
        assert result == 5
        assert myfunc.__doc__ == "myfunc"

    def test_two_decorators(self, PluggableDecorator, config):
        config['decorator_list'] = [
            'palladium.tests.test_util.dec1',
            'palladium.tests.test_util.dec2']
        decorator = PluggableDecorator('decorator_list')

        @decorator
        def myfunc(a, b):
            """myfunc"""
            return a + b

        result = myfunc(2, 3)
        assert result == 52
        assert myfunc.__doc__ == "myfunc"

    def test_wrapped_empty_list(self, PluggableDecorator, config):
        def myfunc(a, b):
            """myfunc"""
            return a + b

        myfunc2 = PluggableDecorator('decorator_list')(myfunc)
        assert hasattr(myfunc, '__wrapped__') is False
        assert myfunc2.__wrapped__ is myfunc

    def test_wrapped(self, PluggableDecorator, config):
        config['decorator_list'] = [
            'palladium.tests.test_util.dec1',
            'palladium.tests.test_util.dec2']

        def myfunc(a, b):
            """myfunc"""
            return a + b

        myfunc2 = PluggableDecorator('decorator_list')(myfunc)
        assert hasattr(myfunc, '__wrapped__') is False
        assert hasattr(myfunc2, '__wrapped__') is True
        assert myfunc2.__wrapped__ is myfunc


class TestSessionScope:

    def test_success(self):
        from palladium.util import session_scope
        session = Mock()
        with session_scope(session):
            session.query()
        assert session.commit.call_count == 1
        assert session.rollback.call_count == 0
        assert session.close.call_count == 1

    def test_exception(self):
        from palladium.util import session_scope
        session = Mock()
        with pytest.raises(KeyError):
            with session_scope(session):
                raise KeyError('Error')
        assert session.commit.call_count == 0
        assert session.rollback.call_count == 1
        assert session.close.call_count == 1


class TestApplyKwargs:
    @pytest.fixture
    def apply_kwargs(self):
        from palladium.util import apply_kwargs
        return apply_kwargs

    @pytest.fixture
    def myfunc(self):
        calls = []

        def myfunc(one, two, three='three'):
            calls.append((one, two, three))

        myfunc.calls = calls
        return myfunc

    def test_it(self, apply_kwargs, myfunc):
        apply_kwargs(myfunc, one=1, two='two', four=4)
        assert myfunc.calls == [(1, 'two', 'three')]

    def test_typeerror(self, apply_kwargs, myfunc):
        with pytest.raises(TypeError):
            apply_kwargs(myfunc, two='two', four=4)


class TestPartial:
    calls = []

    @classmethod
    def myfunc(cls, one, two, three='three'):
        cls.calls.append((one, two, three))

    @pytest.fixture
    def Partial(self):
        from palladium.util import Partial
        return Partial

    def test_it(self, Partial):
        Partial(self.myfunc, two=2)(one='one')
        assert self.calls == [('one', 2, 'three')]
        self.__class__.calls = []

    def test_dotted(self, Partial):
        Partial('palladium.tests.test_util:TestPartial.myfunc', two=2)(one='one')
        assert self.calls == [('one', 2, 'three')]
        self.__class__.calls = []
