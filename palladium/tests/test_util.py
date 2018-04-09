from datetime import datetime
import threading
from time import sleep
from unittest.mock import Mock
from unittest.mock import patch

from dateutil import rrule
import pytest


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
        sleep(0.005)  # make sure that we're not too fast
        dt1 = datetime.now()
        assert dt0 < store.mtime['somekey'] < dt1
        store['somekey'] = '2'
        sleep(0.005)  # make sure that we're not too fast
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


class TestUpgrade:
    @pytest.fixture
    def upgrade(self):
        from palladium.util import upgrade
        return upgrade

    def test_no_args(self, upgrade):
        persister = Mock()
        upgrade(persister)
        persister.upgrade.assert_called_with(from_version=None)

    def test_from_version(self, upgrade):
        persister = Mock()
        upgrade(persister, from_version='0.1')
        persister.upgrade.assert_called_with(from_version='0.1')

    def test_from_version_and_to_version(self, upgrade):
        persister = Mock()
        upgrade(persister, from_version='0.1', to_version='0.2')
        persister.upgrade.assert_called_with(from_version='0.1',
                                             to_version='0.2')


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


class TestRunJob:
    @pytest.fixture
    def run_job(self):
        from palladium.util import run_job
        return run_job

    @pytest.fixture
    def jobs(self, process_store):
        jobs = process_store['process_metadata']['jobs'] = {}
        yield jobs
        jobs.clear()

    def test_simple(self, run_job, jobs):
        def myfunc(add):
            nonlocal result
            result += add
            return add

        result = 0
        results = []
        for i in range(3):
            results.append(run_job(myfunc, add=i))
        sleep(0.005)
        assert result == 3
        assert len(jobs) == len(results) == 3
        assert set(jobs.keys()) == set(r[1] for r in results)
        assert all(j['status'] == 'finished' for j in jobs.values())
        assert set(j['info'] for j in jobs.values()) == set(['0', '1', '2'])

    def test_exception(self, run_job, jobs):
        def myfunc(divisor):
            nonlocal result
            result /= divisor

        result = 1
        num_threads_before = len(threading.enumerate())
        for i in range(3):
            run_job(myfunc, divisor=i)
        sleep(0.005)
        num_threads_after = len(threading.enumerate())

        assert num_threads_before == num_threads_after
        assert result == 0.5
        job1, job2, job3 = sorted(jobs.values(), key=lambda x: x['started'])
        assert job1['status'] == 'error'
        assert 'division by zero' in job1['info']
        assert job2['status'] == 'finished'
        assert job3['status'] == 'finished'

    def test_lifecycle(self, run_job, jobs):
        def myfunc(tts):
            sleep(tts)

        num_threads_before = len(threading.enumerate())
        for i in range(3):
            run_job(myfunc, tts=i/100)

        job1, job2, job3 = sorted(jobs.values(), key=lambda x: x['started'])
        assert job1['status'] == 'finished'
        assert job2['status'] == job3['status'] == 'running'
        assert len(threading.enumerate()) - num_threads_before == 2

        sleep(0.015)
        assert job2['status'] == 'finished'
        assert job3['status'] == 'running'
        assert len(threading.enumerate()) - num_threads_before == 1

        sleep(0.015)
        assert job3['status'] == 'finished'
        assert len(threading.enumerate()) - num_threads_before == 0
