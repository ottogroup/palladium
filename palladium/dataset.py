""":class:`~palladium.interfaces.DatasetLoader` implementations.
"""

import pandas.io.parsers
import pandas.io.sql
from sqlalchemy import create_engine

from .interfaces import DatasetLoader
from .util import logger
from .util import PluggableDecorator
from .util import process_store
from .util import RruleThread


class Table(DatasetLoader):
    """A :class:`~palladium.interfaces.DatasetLoader` that uses
    :func:`pandas.io.parsers.read_table` to load data from a file or
    URL.
    """
    pandas_read = staticmethod(pandas.io.parsers.read_table)

    def __init__(self, path, target_column=None,
                 ndarray=True, **kwargs):
        """
        :param str path:
          The *path* represents a filesystem path or URL that's passed
          on as the *filepath_or_buffer* argument to
          :func:`read_table`.

        :param str target_column:
          The column in the table to load that represents the target
          value.  This column will not be part of the returned *data*.

          If *target_column* is None, then the target return value
          will be None as well.

        :param kwargs:
          All other keyword parameters are passed on to
          :func:`pandas.io.parsers.read_table`.  The most useful
          options may be *usecols* to select which columns of the
          table to use, *skiprows* to skip a certain number of rows at
          the beginning and *nrows* to select a given number of rows
          only.
        """
        self.path = path
        self.target_column = target_column
        self.ndarray = ndarray
        self.kwargs = kwargs

    def __call__(self):
        """See :meth:`palladium.interfaces.DatasetLoader.__call__`.
        """
        df = self.pandas_read(self.path, **self.kwargs)
        data_columns = [col for col in df.columns if col != self.target_column]
        data = df[data_columns]
        target = None
        if self.target_column:
            target = df[self.target_column]
        if self.ndarray:
            return data.values, target.values if target is not None else None
        else:
            return data, target


class SQL(DatasetLoader):
    """A :class:`~palladium.interfaces.DatasetLoader` that uses
    :func:`pandas.io.sql.read_sql` to load data from an SQL database.
    Supports all databases that SQLAlchemy has support for.
    """
    pandas_read = staticmethod(pandas.io.sql.read_sql)

    def __init__(self, url, sql, target_column=None, ndarray=True, **kwargs):
        """
        :param str url:
          The database *url* that'll be used to make a connection.
          Format follows RFC-1738.

        :param str sql:
          SQL query to be executed or database table name.

        :param str target_column:
          The name of the column used as the target.  (All other
          columns are considered feature data.)

        :param kwargs:
          All other keyword parameters are passed on to
          :func:`pandas.io.parsers.read_sql`.
        """
        self.engine = create_engine(url)
        self.sql = sql
        self.target_column = target_column
        self.ndarray = ndarray
        self.kwargs = kwargs

    def __call__(self):
        """See :meth:`palladium.interfaces.DatasetLoader.__call__`.
        """
        df = self.pandas_read(self.sql, self.engine, **self.kwargs)
        data_columns = [col for col in df.columns if col != self.target_column]
        data = df[data_columns]
        target = None
        if self.target_column:
            target = df[self.target_column]
        if self.ndarray:
            return data.values, target.values if target is not None else None
        else:
            return data, target


class EmptyDatasetLoader(DatasetLoader):
    """This :class:`~palladium.interfaces.DatasetLoader` can be used if no
    actual data should be loaded.  Returns a ``(None, None)`` tuple.
    """
    def __call__(self):
        return None, None


class ScheduledDatasetLoader(DatasetLoader):
    """A :class:`~palladium.interfaces.DatasetLoader` that loads
    periodically data into RAM to make it available to the prediction
    server inside the ``process_store``.

    :class:`~ScheduledDatasetLoader` wraps another
    :class:`~palladium.interfaces.DatasetLoader` class that it uses to do
    the actual loading of the data.

    An *update_cache_rrule* is used to define how often data should be
    loaded anew.

    This class' :meth:`~ScheduledDatasetLoader.read` read method never
    calls the underlying dataset loader.  It will only ever fetch the
    data from the in-memory cache.
    """
    cache = process_store
    key = 'data'

    def __init__(self,
                 impl,
                 update_cache_rrule,
                 ):
        """
        :param palladium.interfaces.DatasetLoader impl:
          The underlying (decorated) dataset loader object.

        :param dict update_cache_rrule:
          Keyword arguments for a :class:`dateutil.rrule.rrule` that
          determines when the cache will be updated.  See
          :class:`~palladium.util.RruleThread` for details.
        """
        self.impl = impl
        self.update_cache_rrule = update_cache_rrule

    def initialize_component(self, config):
        self.update_cache()
        logger.info("{}: initial fill of cache done.".format(
            self.__class__.__name__))

        self.thread = RruleThread(
            func=self.update_cache, rrule=self.update_cache_rrule)
        self.thread.start()

    def __call__(self):
        return self.cache[self.key]

    @PluggableDecorator('update_data_decorators')
    def update_cache(self, *args, **kwargs):
        data = self.impl()
        self.cache[self.key] = data
        return data
