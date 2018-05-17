""":class:`~palladium.interfaces.ModelPersister` implementations.
"""

from abc import abstractmethod
import base64
from contextlib import contextmanager
import gzip
import io
import json
import os
import pickle
import codecs
from pkg_resources import parse_version
from tempfile import TemporaryFile
from threading import Lock

import requests
from sqlalchemy import create_engine
from sqlalchemy import CLOB
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.types import TypeDecorator

from . import __version__
from .interfaces import annotate
from .interfaces import ModelPersister
from .util import logger
from .util import PluggableDecorator
from .util import process_store
from .util import RruleThread
from .util import session_scope


class UpgradeSteps:
    def __init__(self):
        self.steps = []

    def add(self, version):
        def decorator(func):
            self.steps.append((parse_version(version), func))
            return func
        return decorator

    def run(self, persister, from_version, to_version):
        from_version = parse_version(from_version)
        to_version = parse_version(to_version)
        results = []
        for version, func in sorted(self.steps):
            if from_version < version <= to_version:
                results.append(func(persister))
        return results


class FileLikeIO:
    """Used by :class:`FileLike` to access low level file handle
    operations.
    """

    @abstractmethod
    def open(self, path, mode='r'):
        """Return a file handle

        For normal files, the implementation is:

        ```python
        return open(path, mode)
        ```
        """

    @abstractmethod
    def exists(self, path):
        """Test whether a path exists

        For normal files, the implementation is:

        ```python
        return os.path.exists(path)
        ```
        """

    @abstractmethod
    def remove(self, path):
        """Remove a file

        For normal files, the implementation is:

        ```python
        os.remove(path)
        ```
        """


class FileIO(FileLikeIO):
    def open(self, path, mode='r'):
        return open(path, mode)

    def exists(self, path):
        return os.path.exists(path)

    def remove(self, path):
        os.remove(path)


class RestIO(FileLikeIO):
    def __init__(self, auth):
        self.session = requests.Session()
        self.session.auth = auth

    @contextmanager
    def _write(self, url, mode):
        # Use a context manager to send the actual request out once
        # the file that FileLike writes into is 'closed'.
        if '+' not in mode:
            mode += '+'
        with TemporaryFile(mode=mode) as fh:
            yield fh
            fh.seek(0)
            res = self.session.put(url, data=fh)
        res.raise_for_status()

    def open(self, path, mode='r'):
        if mode[0] == 'r':
            res = self.session.get(path, stream=True)
            res.raise_for_status()
            if 'b' in mode:
                return res.raw
            else:
                reader = codecs.getreader(res.encoding or 'utf-8')
                return reader(res.raw)
        elif mode[0] == 'w':
            return self._write(path, mode=mode)
        raise NotImplementedError("filemode: %s" % (mode,))

    def exists(self, path):
        res = self.session.head(path)
        if res.status_code == 404:
            return False
        res.raise_for_status()
        return True

    def remove(self, path):
        res = self.session.delete(path)
        res.raise_for_status()


class FileLike(ModelPersister):
    """A :class:`~palladium.interfaces.ModelPersister` that pickles
    models through file-like handles.

    An argument ``io`` is used to access low level file handle
    operations.
    """
    upgrade_steps = UpgradeSteps()

    def __init__(self, path, io):
        """
        :param str path:
          The *path* template that I will use to store models,
          e.g. ``/path/to/model-{version}``.

        :param FileLikeIO io:
          Used to access low level file handle operations.
        """
        if '{version}' not in path:
            raise ValueError(
                "Your file persister path must have a {version} placeholder,"
                "e.g., model-{version}.pickle."
                )
        self.path = path
        self.io = io

    def read(self, version=None):
        use_active_model = version is None

        if version is None:
            props = self.list_properties()
            if 'active-model' not in props:
                raise LookupError("No active model available")
            version = props['active-model']

        fname = self.path.format(version=version) + '.pkl.gz'
        if not self.io.exists(fname):
            if use_active_model:
                raise LookupError(
                    "Activated model not available. Maybe it was deleted.")
            else:
                raise LookupError("No such version: {}".format(version))

        with self.io.open(fname, 'rb') as fh:
            with gzip.open(fh, 'rb') as f:
                return pickle.load(f)

    def write(self, model):
        last_version = 0
        li = self.list_models()
        if li:
            last_version = li[-1]['version']

        version = last_version + 1
        li.append(annotate(model, {'version': version}))

        fname = self.path.format(version=version) + '.pkl.gz'
        with self.io.open(fname, 'wb') as fh:
            with gzip.open(fh, 'wb') as f:
                pickle.dump(model, f)

        self._update_md({'models': li})
        return version

    def list_models(self):
        return self._read_md()['models']

    def list_properties(self):
        return self._read_md()['properties']

    def activate(self, version):
        md = self._read_md()
        md['properties']['active-model'] = str(version)
        versions = [m['version'] for m in md['models']]
        if int(version) not in versions:
            raise LookupError("No such version: {}".format(version))
        self._update_md({'properties': md['properties']})

    def delete(self, version):
        md = self._read_md()
        versions = [m['version'] for m in md['models']]
        version = int(version)
        if version not in versions:
            raise LookupError("No such version: {}".format(version))
        self._update_md({
            'models': [m for m in md['models'] if m['version'] != version]})
        self.io.remove(self.path.format(version=version) + '.pkl.gz')

    @property
    def _md_filename(self):
        return self.path.format(version='metadata') + '.json'

    def _read_md(self):
        if self.io.exists(self._md_filename):
            with self.io.open(self._md_filename, 'r') as f:
                return json.load(f)
        return {'models': [], 'properties': {'db-version': __version__}}

    def _update_md(self, data):
        data2 = self._read_md()
        data2.update(data)
        with self.io.open(self._md_filename, 'w') as f:
            json.dump(data2, f, indent=4)

    def upgrade(self, from_version=None, to_version=__version__):
        if from_version is None:
            try:
                from_version = self._read_md()['properties']['db-version']
            except (KeyError, TypeError):
                from_version = "0.0"

        self.upgrade_steps.run(self, from_version, to_version)
        md = self._read_md()
        md['properties']['db-version'] = to_version
        self._update_md(md)

    @upgrade_steps.add('1.0')
    def _upgrade_1_0(self):
        if self.io.exists(self._md_filename):
            with self.io.open(self._md_filename, 'r') as f:
                old_md = json.load(f)
        else:
            old_md = None

        active_model = old_md[-1]['version'] if old_md else None
        new_md = {
            'models': old_md or [],
            'properties': {},
            }
        if active_model is not None:
            new_md['properties']['active-model'] = str(active_model)

        with self.io.open(self._md_filename, 'w') as f:
            json.dump(new_md, f, indent=4)


class File(FileLike):
    """A :class:`~palladium.interfaces.ModelPersister` that pickles models
    onto the file system, into a given directory.
    """
    def __init__(self, path):
        """
        :param str path:
          The *path* template that I will use to store models,
          e.g. ``/path/to/model-{version}``.
        """
        super().__init__(path, FileIO())


class Rest(FileLike):
    def __init__(self, url, auth):
        super().__init__(url, RestIO(auth))


class Database(ModelPersister):
    """A :class:`~palladium.interfaces.ModelPersister` that pickles models
    into an SQL database.
    """

    upgrade_steps = UpgradeSteps()

    def __init__(
            self, url, poolclass=None, chunk_size=1024 ** 2 * 100,
            table_postfix=''):
        """
        :param str url:
          The database *url* that'll be used to make a connection.
          Format follows RFC-1738.  I'll create a table ``models`` to
          store the pickles in if it doesn't exist yet.

        :param sqlalchemy.pool.Pool poolclass:
          A class specifying DB connection behavior of the engine. If set to
          None, the NullPool will be used.

        :param int chunk_size:
          The pickled contents of the model are stored inside the
          database in chunks.  The default size is 1024 ** 2 * 100
          (100MB).

        :param str table_postfix:
          If *table_postfix* is provided, I will append it to the
          table name of all tables used in this instance.
        """
        if not poolclass:
            poolclass = NullPool
        engine = create_engine(url, poolclass=poolclass)
        self.engine = engine
        self.chunk_size = chunk_size
        self.table_postfix = table_postfix
        self.write_lock = Lock()
        orms = self.create_orm_classes()
        self.Property = orms['Property']
        self.DBModel = orms['DBModel']
        self.DBModelChunk = orms['DBModelChunk']
        metadata = self.DBModel.metadata
        metadata.bind = engine
        metadata.create_all()
        self.session = scoped_session(sessionmaker(bind=engine))
        self._initialize_properties()

    def _initialize_properties(self):
        with session_scope(self.session) as session:
            if session.query(self.Property).count() == 0:
                self._set_property('db-version', __version__)

    def _table_postfix(self, name):
        if self.table_postfix:
            return '{}_{}'.format(name, self.table_postfix)
        else:
            return name

    def create_orm_classes(self):
        Base = declarative_base()

        return {
            'Base': Base,
            'Property': self.PropertyClass(Base),
            'DBModel': self.DBModelClass(Base),
            'DBModelChunk': self.DBModelChunkClass(Base),
            }

    def PropertyClass(self, Base):
        class Property(Base):
            __tablename__ = self._table_postfix('properties')
            id = Column(Integer, primary_key=True)
            name = Column(String(length=10 ** 3))
            value = Column(String(length=10 ** 3), nullable=False)
        return Property

    def DBModelClass(self, Base):
        class DBModel(Base):
            __tablename__ = self._table_postfix('models')
            version = Column(Integer, primary_key=True)
            metadata_ = Column(
                'metadata', String(length=10 ** 6), nullable=False)
            chunks = relationship(
                'DBModelChunk',
                order_by="DBModelChunk.id",
                )
        return DBModel

    def DBModelChunkClass(self, Base):
        class DBModelChunk(Base):
            __tablename__ = self._table_postfix('model_chunks')
            id = Column(Integer, primary_key=True)
            model_version = Column(
                ForeignKey('{}.version'.format(self._table_postfix('models'))))
            blob = Column(LargeBinary, nullable=False)
        return DBModelChunk

    def read(self, version=None):
        use_active_model = version is None

        with session_scope(self.session) as session:
            query = session.query(self.DBModel)
            if not version:
                version = self._active_version
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

        if use_active_model and dbmodel is None and version is not None:
            raise LookupError(
                "Activated model not available. Maybe it was deleted.")

        raise LookupError("No model available")

    def write(self, model):
        with self.write_lock:
            return self._write(model)

    def _write(self, model):
        max_version = self._get_max_version()
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

    def _get_max_version(self):
        # We retrieve the max version by hand instead of using an
        # auto-increment because we want to annotate the version
        # number onto the model's metadata.
        with session_scope(self.session) as session:
            query = session.query(self.DBModel.version)
            result = query.order_by(self.DBModel.version.desc()).first()

        if result is not None:
            return result[0]

    def list_models(self):
        with session_scope(self.session) as session:
            results = session.query(self.DBModel.metadata_).all()
        infos = [json.loads(res[0]) for res in results]
        return sorted(infos, key=lambda x: x['version'])

    def list_properties(self):
        with session_scope(self.session) as session:
            return {prop.name: prop.value
                    for prop in session.query(self.Property)}

    def activate(self, version):
        self._set_property('active-model', str(version))

    def delete(self, version):
        with session_scope(self.session) as session:
            session.query(self.DBModel).filter_by(version=version).delete()

    @property
    def _active_version(self):
        with session_scope(self.session) as session:
            active_model = session.query(self.Property).filter_by(
                name='active-model').first()
            if active_model is not None:
                return int(active_model.value)

    def _set_property(self, name, value):
        with session_scope(self.session) as session:
            prop = session.query(self.Property).filter_by(name=name).first()
            if prop is None:
                session.add(self.Property(name=name, value=str(value)))
            else:
                prop.value = str(value)
                session.add(prop)

    def upgrade(self, from_version=None, to_version=__version__):
        if from_version is None:
            from_version = self.list_properties().get('db-version', '0.0')

        self.upgrade_steps.run(self, from_version, to_version)
        self._set_property('db-version', to_version)

    @upgrade_steps.add('1.0')
    def _upgrade_1_0(self):
        if self.list_properties().get('active-model') is None:
            models = self.list_models()
            if models:
                self.activate(int(models[-1]['version']))


class DatabaseCLOB(Database):
    """A :class:`~palladium.interfaces.ModelPersister` derived from
    :class:`Database`, with only the slight difference of using
    CLOB instead of BLOB to store the pickle data.

    Use when BLOB is not available.
    """
    class BytesToBase64Type(TypeDecorator):
        impl = CLOB

        def process_bind_param(self, value, dialect):
            if value is not None:
                value = base64.b64encode(bytes(value)).decode('ascii')
            return value

        def process_result_value(self, value, dialect):
            if value is not None:
                value = base64.b64decode(value.encode('ascii'))
            return value

    def DBModelChunkClass(self, Base):
        class DBModelChunk(Base):
            __tablename__ = self._table_postfix('model_chunks')
            id = Column(Integer, primary_key=True)
            model_version = Column(
                ForeignKey('{}.version'.format(self._table_postfix('models'))))
            blob = Column(self.BytesToBase64Type(String()), nullable=False)
        return DBModelChunk


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
    __pld_config_key__ = 'cachedupdatepersister_default'
    _loaded_version = None

    def __init__(self,
                 impl,
                 update_cache_rrule=None,
                 check_version=True,
                 ):
        """
        :param ModelPersister impl:
          The underlying (decorated) persister object.

        :param dict update_cache_rrule:
          Optional keyword arguments for a
          :class:`dateutil.rrule.rrule` that determines when the cache
          will be updated.  See :class:`~palladium.util.RruleThread` for
          details.

        :param bool check_version:
          If set to `True`, I will perform a check and only load a new
          model from the storage if my cached version differs from
          what's the current active version.
        """
        self.impl = impl
        self.update_cache_rrule = update_cache_rrule
        self.check_version = check_version

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
            return self.cache[self.__pld_config_key__]
        else:
            return self.impl.read(*args, **kwargs)

    @PluggableDecorator('update_model_decorators')
    def update_cache(self, *args, **kwargs):
        active_version = None

        if self.check_version:
            active_version = self.list_properties().get('active-model')
            if self._loaded_version == (active_version, args, kwargs):
                return

        try:
            model = self.impl.read(*args, **kwargs)
        except LookupError:
            model = None
        if model is not None:
            self.cache[self.__pld_config_key__] = model

            if self.check_version:
                self._loaded_version = (active_version, args, kwargs)

            return model

    def write(self, model):
        return self.impl.write(model)

    def list_models(self):
        return self.impl.list_models()

    def list_properties(self):
        return self.impl.list_properties()

    def activate(self, version):
        return self.impl.activate(version)

    def delete(self, version):
        return self.impl.delete(version)

    def upgrade(self, from_version=None, to_version=__version__):
        return self.impl.upgrade(from_version, to_version)
