from multiprocessing.pool import ThreadPool
from unittest.mock import Mock

import numpy as np
import pandas
import pytest


class TestDiskCache:
    @pytest.fixture
    def diskcache(self):
        from palladium.cache import diskcache
        return diskcache

    def test_it(self, diskcache, tmpdir):
        called = []

        @diskcache(lambda x: 'key_{}'.format(x))
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        cache = squareit.__cache__
        cache.filename_tmpl = (
            f'{tmpdir}/{{module}}.{{func}}-cache-{{key}}.cache')

        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert called == [2, 3]

    def test_it_no_compute_key(self, diskcache, tmpdir):
        called = []

        @diskcache()
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        cache = squareit.__cache__
        cache.filename_tmpl = (
            f'{tmpdir}/{{module}}.{{func}}-cache-{{key}}.cache')

        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert called == [2, 3]

    def test_it_ignore(self, diskcache, tmpdir):
        called = []

        @diskcache(ignore=True)
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        cache = squareit.__cache__
        cache.filename_tmpl = (
            f'{tmpdir}/{{module}}.{{func}}-cache-{{key}}.cache')

        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert called == [2, 3, 3]

    def test_it_filename(self, diskcache, tmpdir):
        called = []

        @diskcache(filename_tmpl=str(tmpdir.join('filename-{key}')))
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        assert len(tmpdir.listdir()) == 0
        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert len(tmpdir.listdir()) > 0
        assert called == [2, 3]

    def test_it_bad_filename(self, diskcache):
        with pytest.raises(ValueError):
            diskcache(filename_tmpl='string-without-key')

    def test_concurrency(self, diskcache, tmpdir):
        called = []

        df = pandas.DataFrame(np.zeros(1_000_000))

        @diskcache(lambda x: 'key_{}'.format(x))
        def something(x):
            called.append(x)
            return df

        cache = something.__cache__
        cache.filename_tmpl = (
            f'{tmpdir}/{{module}}.{{func}}-cache-{{key}}.cache')

        pool = ThreadPool(9)
        result = pool.map(something, [2] * 18)
        assert all([df.equals(res) for res in result])


class TestPickleDiskCache(TestDiskCache):
    @pytest.fixture
    def diskcache(self):
        from palladium.cache import picklediskcache
        return picklediskcache


class TestComputeKeyAttrs:
    @pytest.fixture
    def compute_key_attrs(self):
        from palladium.cache import compute_key_attrs
        return compute_key_attrs

    def test_it(self, compute_key_attrs):
        compute_key = compute_key_attrs(['one', 'two'])
        compute_key(Mock(one=1, two=2, three=3)) == (1, 2)
