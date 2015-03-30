""":class:`~palladium.interfaces.ModelPersister` implementations.
"""

import gzip
import io
import json
import os
import pickle
import re
from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from .interfaces import annotate
from .interfaces import ModelPersister
from .util import logger
from .util import PluggableDecorator
from .util import process_store
from .util import RruleThread
from .util import session_scope


Base = declarative_base()


class File(ModelPersister):
    """A :class:`~palladium.interfaces.ModelPersister` that pickles models
    onto the file system, into a given directory.
    """

    def __init__(self, path):
        """
        :param str path:
          The *path* template that I will use to store models,
          e.g. ``/path/to/model-{version}``.
        """
        if path.find('{version}') < 0:
            raise ValueError(
                "Your file persister path must have a {version} placeholder,"
                "e.g., model-{version}.pickle."
                )
        self.path = path

    def read(self, version=None):
        if version is None:
            li = self.list()
            if not li:
                raise IOError("No model available")
            version = li[-1]['version']

        fname = self.path.format(version=version) + '.pkl.gz'
        with gzip.open(fname, 'rb') as f:
            return pickle.load(f)

    def write(self, model):
        last_version = 0
        li = self.list()
        if li:
            last_version = li[-1]['version']

        version = last_version + 1
        li.append(annotate(model, {'version': version}))

        fname = self.path.format(version=version) + '.pkl.gz'
        with gzip.open(fname, 'wb') as f:
            pickle.dump(model, f)

        self._write_md(li)
        return version

    def list(self):
        fname = self.path.format(version='metadata') + '.json'
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                return json.load(f)
        else:
            return []

    def _write_md(self, li):
        fname = self.path.format(version='metadata') + '.json'
        with open(fname, 'w') as f:
            json.dump(li, f, indent=4)


class Database(ModelPersister):
    """A :class:`~palladium.interfaces.ModelPersister` that pickles models
    into an SQL database.
    """

    write_lock = Lock()

    class DBModel(Base):
        __tablename__ = 'models'
        version = Column(Integer, primary_key=True)
        metadata_ = Column('metadata', String(length=10 ** 6), nullable=False)
        chunks = relationship(
            'DBModelChunk',
            order_by="DBModelChunk.id",
            )

    class DBModelChunk(Base):
        __tablename__ = 'model_chunks'
        id = Column(Integer, primary_key=True)
        model_version = Column(ForeignKey('models.version'))
        blob = Column(LargeBinary, nullable=False)

    def __init__(self, url, chunk_size=1024 ** 2 * 100):
        """
        :param str url:
          The database *url* that'll be used to make a connection.
          Format follows RFC-1738.  I'll create a table ``models`` to
          store the pickles in if it doesn't exist yet.

        :param int chunk_size:
          The pickled contents of the model are stored inside the
          database in chunks.  The default size is 1024 ** 2 * 100
          (100MB).
        """
        engine = create_engine(url)
        self.engine = engine
        metadata = self.DBModel.metadata
        metadata.bind = engine
        metadata.create_all()
        self.session = scoped_session(sessionmaker(bind=engine))
        self.chunk_size = chunk_size

    def read(self, version=None):
        with session_scope(self.session) as session:
            query = session.query(self.DBModel)
            if not version:
                dbmodel = query.order_by(self.DBModel.version.desc()).first()
            else:
                dbmodel = query.filter_by(version=version).first()

            if dbmodel is not None:
                query2 = session.query(self.DBModelChunk).filter_by(
                    model_version=dbmodel.version
                    ).order_by('id').yield_per(4)
                fileobj = io.BytesIO()
                for chunk in query2:
                    fileobj.write(chunk.blob)
                fileobj.seek(0)
                return pickle.load(gzip.GzipFile(fileobj=fileobj, mode='rb'))

        raise IOError("No model available")

    def write(self, model):
        with self.write_lock:
            return self._write(model)

    def _write(self, model):
        max_version = self.get_max_version()
        if not max_version:
            max_version = 0
        version = max_version + 1

        annotate(model, {'version': version})

        fileobj = io.BytesIO()
        pickle.dump(model, gzip.GzipFile(fileobj=fileobj, mode='wb'))
        data = fileobj.getbuffer()
        chunks = [data[i:i + self.chunk_size]
                  for i in range(0, len(data), self.chunk_size)]

        dbmodel = self.DBModel(
            version=version,
            chunks=[self.DBModelChunk(blob=chunk) for chunk in chunks],
            metadata_=json.dumps(model.__metadata__),
            )

        with session_scope(self.session) as session:
            session.add(dbmodel)

        return version

    def list(self):
        with session_scope(self.session) as session:
            results = session.query(self.DBModel.metadata_).all()
        infos = [json.loads(res[0]) for res in results]
        return sorted(infos, key=lambda x: x['version'])

    def get_max_version(self):
        # We retrieve the max version by hand instead of using an
        # auto-increment because we want to annotate the version
        # number onto the model's metadata.
        with session_scope(self.session) as session:
            query = session.query(self.DBModel.version)
            result = query.order_by(self.DBModel.version.desc()).first()

        if result is not None:
            return result[0]


class CachedUpdatePersister(ModelPersister):
    """A :class:`~palladium.interfaces.ModelPersister` that serves as a
    caching decorator around another `~palladium.interfaces.ModelPersister`
    object.

    Calls to :meth:`~CachedUpdatePersister.read` will look up a model from
    the global ``process_store``, i.e. there is never any actual
    loading involved when calling :meth:`~CachedUpdatePersister.read`.

    To fill the ``process_store`` cache periodically using the return
    value of the underlying :class:`~palladium.interfaces.ModelPersister`'s
    ``read`` method, a dictionary containing keyword arguments to
    :class:`dateutil.rrule.rrule` may be passed.  The cache will then
    be filled periodically according to that recurrence rule.

    If no *update_cache_rrule* is used, the :class:`CachedUpdatePersister`
    will call once and remember the return value of the underlying
    :class:`~palladium.interfaces.ModelPersister`'s ``read`` method during
    initialization.
    """

    cache = process_store
    key = 'model'

    def __init__(self,
                 impl,
                 update_cache_rrule=None
                 ):
        """
        :param ModelPersister impl:
          The underlying (decorated) persister object.

        :param dict update_cache_rrule:
          Optional keyword arguments for a
          :class:`dateutil.rrule.rrule` that determines when the cache
          will be updated.  See :class:`~palladium.util.RruleThread` for
          details.
        """
        self.impl = impl
        self.update_cache_rrule = update_cache_rrule

    def initialize_component(self, config):
        self.use_cache = config.get('__mode__') != 'fit'
        self.thread = None

        if not self.use_cache:
            return

        self.update_cache()
        logger.info("{}: initial fill of cache done.".format(
            self.__class__.__name__))

        if self.update_cache_rrule:
            self.thread = RruleThread(
                func=self.update_cache, rrule=self.update_cache_rrule)
            self.thread.start()

    def read(self, *args, **kwargs):
        if self.use_cache:
            return self.cache[self.key]
        else:
            return self.impl.read(*args, **kwargs)

    @PluggableDecorator('update_model_decorators')
    def update_cache(self, *args, **kwargs):
        model = self.impl.read(*args, **kwargs)
        if model is not None:
            self.cache[self.key] = model
            return model

    @PluggableDecorator('write_model_decorators')
    def write(self, model):
        return self.impl.write(model)

    def list(self):
        return self.impl.list()
