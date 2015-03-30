from random import random

import pandas
import pytest


class TestDiskCache:
    @pytest.fixture
    def diskcache(self):
        from palladium.cache import diskcache
        return diskcache

    def test_it(self, diskcache):
        called = []

        @diskcache(lambda x: 'key_{}'.format(x))
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        cache = squareit.__cache__
        cache.filename_tmpl = '/tmp/{module}.{func}-cache-{key}-%s.cache' % (
            str(random()),)

        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert called == [2, 3]

    def test_it_no_compute_key(self, diskcache):
        called = []

        @diskcache()
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        cache = squareit.__cache__
        cache.filename_tmpl = '/tmp/{module}.{func}-cache-{key}-%s.cache' % (
            str(random()),)

        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert called == [2, 3]

    def test_it_ignore(self, diskcache):
        called = []

        @diskcache(ignore=True)
        def squareit(x):
            called.append(x)
            return pandas.DataFrame([x ** 2])

        cache = squareit.__cache__
        cache.filename_tmpl = '/tmp/{module}.{func}-cache-{key}-%s.cache' % (
            str(random()),)

        assert (squareit(2).squeeze(),
                squareit(3).squeeze(),
                squareit(3).squeeze()) == (4, 9, 9)
        assert called == [2, 3, 3]


class TestPickleDiskCache(TestDiskCache):
    @pytest.fixture
    def diskcache(self):
        from palladium.cache import picklediskcache
        return picklediskcache
