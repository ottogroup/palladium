"""The cache module provides caching utilities in order to provide
faster access to data which is needed repeatedly.  The disk cache
(:class:`diskcache`) which is primarily used during development when
loading data from the local harddisk is faster than querying a remote
database.
"""

import hashlib
from functools import wraps
import os
import pickle
from tempfile import gettempdir

from joblib import numpy_pickle


class abstractcache(object):
    """
    An abstract class for providing basic functionality for caching
    function calls. It contains the handling of keys used for
    caching objects.
    """
    cache = None  # a dict-like that has to be implemented

    def __init__(self, compute_key=None, ignore=False):
        self.compute_key = compute_key
        self.ignore = ignore

    def __call__(self, func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if self.ignore() if callable(self.ignore) else self.ignore:
                return func(*args, **kwargs)

            if self.compute_key is not None:
                key = self.compute_key(*args, **kwargs)
            else:
                key = args, tuple(kwargs.items())
            try:
                return self.cache[key]
            except KeyError:
                pass

            value = func(*args, **kwargs)
            self.cache[key] = value
            return value

        self.func = func
        wrapped.__cache__ = self
        return wrapped

    def __len__(self):  # pragma: no cover
        raise NotImplementedError()


class diskcache(abstractcache):
    """
    The disk cache stores results of function calls as pickled files
    to disk.  Usually used during development and evaluation to save
    costly DB interactions in repeated calls with the same data.

    Note: Should changes to the database or to your functions require
    you to purge existing cached values, then those cache files are
    found in the location defined in :attr:`filename_tmpl`.
    """
    def __init__(self, *args, filename_tmpl=None, **kwargs):
        """
        :param str filename_tmpl:
          The filename template that I will use to store cache files,
          e.g. ``{}``.
        """.format(diskcache.filename_tmpl)
        super().__init__(*args, **kwargs)
        if filename_tmpl is not None:
            if '{key}' not in filename_tmpl:
                raise ValueError(
                    "Your filename_tmpl must have a {key} placeholder,"
                    "e.g., cache-{key}.pickle."
                    )
            self.filename_tmpl = filename_tmpl

    #: Where to persist cached values
    filename_tmpl = gettempdir() + '/pld/cache-{module}.{func}-{key}.pickle'

    #: Using numpy_pickle.load
    load = staticmethod(numpy_pickle.load)

    #: Using numpy_pickle.dump
    dump = staticmethod(numpy_pickle.dump)

    @property
    def cache(self):
        return self

    def _filename(self, key):
        hashed_key = hashlib.sha1(str(key).encode('utf-8')).hexdigest()[:8]
        return self.filename_tmpl.format(
            module=self.func.__module__,
            func=self.func.__name__,
            key=hashed_key,
            )

    def __getitem__(self, key):
        filename = self._filename(key)
        if os.path.exists(filename):
            return self.load(filename)
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        filename = self._filename(key)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        return self.dump(value, filename)


class picklediskcache(diskcache):
    """
    Same as diskcache, except that standard pickle is used instead of
    joblib's pickle functionality.
    """
    def load(self, filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)

    def dump(self, value, filename):
        with open(filename, 'wb') as f:
            return pickle.dump(value, f, -1)


def compute_key_attrs(attrs):
    def compute_key(self, *args, **kwargs):
        return tuple(getattr(self, attr) for attr in attrs)
    return compute_key
