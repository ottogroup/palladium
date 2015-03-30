import gzip
import json
import os
import pickle
from threading import Thread
from unittest.mock import Mock
from unittest.mock import MagicMock
from unittest.mock import patch
from time import sleep

import pytest


class Dummy:
    def __init__(self, **kwargs):
        vars(self).update(kwargs)

    def __eq__(self, other):
        return vars(self) == vars(other)


class TestFile:
    @pytest.fixture
    def File(self):
        from palladium.persistence import File
        return File

    def test_init_path_without_version(self, File):
        with pytest.raises(ValueError):
            filepersister = File('path_without')

    def test_read(self, File):
        with patch('palladium.persistence.File.list') as list,\
            patch('palladium.persistence.gzip.open') as open,\
            patch('palladium.persistence.pickle.load') as load:
            list.return_value = [{'version': 99}]
            open.return_value = MagicMock()
            result = File('/models/model-{version}').read()
            open.assert_called_with('/models/model-99.pkl.gz', 'rb')
            assert result == load.return_value
            load.assert_called_with(open.return_value.__enter__.return_value)

    def test_read_with_version(self, File):
        with patch('palladium.persistence.File.list') as list,\
            patch('palladium.persistence.gzip.open') as open,\
            patch('palladium.persistence.pickle.load') as load:
            list.return_value = [{'version': 99}]
            open.return_value = MagicMock()
            result = File('/models/model-{version}').read(432)
            open.assert_called_with('/models/model-432.pkl.gz', 'rb')
            assert result == load.return_value
            load.assert_called_with(open.return_value.__enter__.return_value)

    def test_read_no_model(self, File):
        with patch('palladium.persistence.File.list') as list:
            list.return_value = []
            f = File('/models/model-{version}')
            with pytest.raises(IOError):
                f.read()

    def test_read_no_model_with_given_version(self, File):
        with patch('palladium.persistence.File.list') as list:
            list.return_value = []
            f = File('/models/model-{version}')
            with pytest.raises(IOError):
                f.read(1)

    def test_write_no_model_files(self, File):
        with patch('palladium.persistence.File.list') as list,\
            patch('palladium.persistence.File._write_md') as write_md,\
            patch('palladium.persistence.gzip.open') as open,\
            patch('palladium.persistence.pickle.dump') as dump:
            list.return_value = []
            open.return_value = MagicMock()
            model = MagicMock()
            result = File('/models/model-{version}').write(model)
            open.assert_called_with('/models/model-1.pkl.gz', 'wb')
            dump.assert_called_with(
                model,
                open.return_value.__enter__.return_value,
                )
            write_md.assert_called_with([model.__metadata__])
            assert result == 1

    def test_write_with_model_files(self, File):
        with patch('palladium.persistence.File.list') as list,\
            patch('palladium.persistence.File._write_md') as write_md,\
            patch('palladium.persistence.gzip.open') as open,\
            patch('palladium.persistence.pickle.dump') as dump:
            list.return_value = [{'version': 99}]
            open.return_value = MagicMock()
            model = MagicMock()
            result = File('/models/model-{version}').write(model)
            open.assert_called_with('/models/model-100.pkl.gz', 'wb')
            dump.assert_called_with(
                model,
                open.return_value.__enter__.return_value,
                )
            write_md.assert_called_with([
                {'version': 99},
                model.__metadata__,
                ])
            assert result == 100

    def test_update_metadata(self, File):
        model = MagicMock(__metadata__={
            'existing': 'entry', 'version': 'overwritten'})

        with patch('palladium.persistence.File.list') as list,\
            patch('palladium.persistence.File._write_md') as write_md,\
            patch('palladium.persistence.gzip.open'),\
            patch('palladium.persistence.pickle.dump'):
            list.return_value = [{'version': 99}]
            File('/models/model-{version}').write(model)
            assert model.__metadata__ == {
                'existing': 'entry',
                'version': 100,
                }
            write_md.assert_called_with([
                {'version': 99},
                model.__metadata__,
                ])

    def test_list_no_metadata(self, File):
        with patch('palladium.persistence.os.path.exists') as exists:
            exists.return_value = False
            assert File('model-{version}').list() == []
            exists.assert_called_with('model-metadata.json')

    def test_list_with_metadata(self, File):
        with patch('palladium.persistence.os.path.exists') as exists,\
            patch('builtins.open') as open,\
            patch('palladium.persistence.json.load') as load:
            exists.return_value = True
            assert File('model-{version}').list() == load.return_value
            exists.assert_called_with('model-metadata.json')
            open.assert_called_with('model-metadata.json', 'r')

    def test_write_md(self, File):
        with patch('builtins.open') as open,\
            patch('palladium.persistence.json.dump') as dump:
            md = [{'hello': 'world'}]
            File('model-{version}')._write_md(md)
            open.assert_called_with('model-metadata.json', 'w')
            dump.assert_called_with(
                md,
                open.return_value.__enter__.return_value,
                indent=4,
                )


class TestDatabase:
    @pytest.fixture
    def Database(self):
        from palladium.persistence import Database
        return Database

    @pytest.fixture
    def database(self, request, Database):
        path = '/tmp/palladium.testing-{}.sqlite'.format(os.getpid())
        request.addfinalizer(lambda: os.remove(path))
        return Database('sqlite:///{}'.format(path), chunk_size=4)

    @pytest.fixture
    def dbmodel(self, database):
        from palladium.util import session_scope

        model = Dummy(
            name='mymodel',
            __metadata__={'some': 'metadata', 'version': 1},
            )

        model_blob = gzip.compress(pickle.dumps(model), compresslevel=0)
        chunk_size = 4
        chunks = [model_blob[i:i + chunk_size]
                  for i in range(0, len(model_blob), chunk_size)]

        dbmodel = database.DBModel(
            version=1,
            chunks=[
                database.DBModelChunk(
                    model_version=1,
                    blob=chunk,
                    )
                for chunk in chunks
                ],
            metadata_=json.dumps(model.__metadata__),
            )

        with session_scope(database.session) as session:
            session.add(dbmodel)

        return model

    def test_read_no_entry(self, database):
        with pytest.raises(IOError):
            database.read()

    def test_read_with_existing_entry(self, database, dbmodel):
        model = database.read()
        assert model == dbmodel

    def test_write_no_entry(self, database):
        model = Dummy(name='mymodel')
        database.write(model)
        assert database.read() == model
        assert model.__metadata__['version'] == 1

    def test_write_with_existing_entry(self, database, dbmodel):
        model = Dummy(name='mymodel')
        database.write(model)
        assert database.read() == model
        assert model.__metadata__['version'] == 2
        assert database.read(1) == dbmodel

    def test_concurrent_read_write(self, database, dbmodel):
        model = Dummy(name='mymodel')

        _read_success = True
        def read():
            nonlocal _read_success
            try:
                database.read()
            except:
                _read_success = False
                raise

        _write_success = True
        def write():
            nonlocal _write_success
            try:
                database.write(model)
            except:
                _write_success = False
                raise

        read_threads = [Thread(target=read) for i in range(5)]
        write_threads = [Thread(target=write) for i in range(5)]

        for th in write_threads:
            th.start()
        for th in read_threads:
            th.start()
        for th in write_threads + read_threads:
            th.join()

        assert _read_success
        assert _write_success

    def test_list_no_entries(self, database):
        assert database.list() == []

    def test_list_with_existing_entry(self, database, dbmodel):
        listing = database.list()
        assert listing == [dbmodel.__metadata__]

    def test_list_with_two_entries(self, database, dbmodel):
        model2 = Dummy(name='mymodel')
        database.write(model2)
        listing = database.list()
        assert listing == [dbmodel.__metadata__, model2.__metadata__]

class TestCachedUpdatePersister:
    @pytest.fixture
    def CachedUpdatePersister(self, process_store):
        from palladium.persistence import CachedUpdatePersister
        return CachedUpdatePersister

    @pytest.fixture
    def persister(self, CachedUpdatePersister, config):
        persister = CachedUpdatePersister(MagicMock())
        persister.initialize_component(config)
        return persister

    def test_read(self, process_store, persister):
        assert persister.read() is persister.impl.read.return_value

    def test_read_custom_value(self, process_store, persister):
        process_store['model'] = 'mymodel'
        assert persister.read() == 'mymodel'

    def test_write(self, persister):
        persister.write('mymodel')
        persister.impl.write.assert_called_with('mymodel')

    def test_update_cache(self, persister):
        persister.update_cache(version=123)
        assert persister.read() is persister.impl.read.return_value
        persister.impl.read.assert_called_with(version=123)

    def test_update_cache_rrule(self, process_store, CachedUpdatePersister,
                                config):
        rrule_info = {
            'freq': 'DAILY',
            'dtstart': '2014-10-30T13:21:18',
            }

        impl = MagicMock()
        persister = CachedUpdatePersister(impl, update_cache_rrule=rrule_info)
        persister.initialize_component(config)
        assert persister.read() is impl.read.return_value
        assert process_store['model'] is impl.read.return_value
        assert impl.read.call_count == 1

    def test_dont_cache(self, process_store, CachedUpdatePersister, config):
        config['__mode__'] = 'fit'

        rrule_info = {
            'freq': 'DAILY',
            'dtstart': '2014-10-30T13:21:18',
            }

        impl = MagicMock()
        persister = CachedUpdatePersister(impl, update_cache_rrule=rrule_info)
        persister.initialize_component(config)
        assert persister.read() is impl.read.return_value
        assert len(process_store) == 0
        assert persister.thread is None

    def test_list(self, CachedUpdatePersister):
        impl = Mock()
        persister = CachedUpdatePersister(impl)
        persister.list() is impl.load.return_value
