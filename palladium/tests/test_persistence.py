import codecs
import copy
import gzip
import json
import os
import pickle
import posixpath
from threading import Thread
from unittest.mock import Mock
from unittest.mock import MagicMock
from unittest.mock import patch

import requests_mock
import pytest

from palladium.interfaces import annotate


class Dummy:
    def __init__(self, **kwargs):
        vars(self).update(kwargs)

    def __eq__(self, other):
        return vars(self) == vars(other)


class TestUpgradeSteps:
    @pytest.fixture
    def steps(self):
        from palladium.persistence import UpgradeSteps
        return UpgradeSteps()

    @pytest.fixture
    def three_steps(self, steps):
        step1, step2, step3 = Mock(), Mock(), Mock()
        steps.add('0.1')(step1)
        steps.add('0.2')(step2)
        steps.add('0.3')(step3)
        return step1, step2, step3, steps

    def test_empty(self, steps):
        results = steps.run(None, '0.1', '1.0')
        assert results == []

    def test_three_steps_overlap(self, three_steps):
        step1, step2, step3, steps = three_steps
        persister = Mock()
        results = steps.run(persister, '0.1', '0.3')
        assert len(results) == 2
        assert results == [step2.return_value, step3.return_value]
        step2.assert_called_with(persister)
        step3.assert_called_with(persister)
        assert step1.call_count == 0

    def test_three_steps_no_overlap(self, three_steps):
        step1, step2, step3, steps = three_steps
        persister = Mock()
        results = steps.run(persister, '0.3', '1.0')
        assert results == []


class TestFile:
    @pytest.fixture
    def File(self, monkeypatch):
        from palladium.persistence import File
        File._update_md_orig = File._update_md
        monkeypatch.setattr(File, '_update_md', Mock())
        return File

    def test_init_path_without_version(self, File):
        with pytest.raises(ValueError):
            File('path_without')

    def test_read(self, File):
        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.File.list_properties') as lp,\
            patch('palladium.persistence.os.path.exists') as exists,\
            patch('palladium.persistence.open') as open,\
            patch('palladium.persistence.annotate') as annotate,\
            patch('palladium.persistence.gzip.open') as gzopen,\
            patch('palladium.persistence.pickle.load') as load:
            lm.return_value = [{'version': 99}]
            lp.return_value = {'active-model': '99'}
            exists.side_effect = lambda fn: fn == '/models/model-99.pkl.gz'
            open.return_value = MagicMock()
            annotate.return_value = {}
            result = File('/models/model-{version}').read()
            open.assert_called_with('/models/model-99.pkl.gz', 'rb')
            assert result == load.return_value
            load.assert_called_with(gzopen.return_value.__enter__.return_value)

    def test_read_with_version(self, File):
        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.os.path.exists') as exists,\
            patch('palladium.persistence.open') as open,\
            patch('palladium.persistence.annotate') as annotate,\
            patch('palladium.persistence.gzip.open') as gzopen,\
            patch('palladium.persistence.pickle.load') as load:
            lm.return_value = [{'version': 99}]
            exists.side_effect = lambda fn: fn == '/models/model-432.pkl.gz'
            open.return_value = MagicMock()
            annotate.return_value = {}
            result = File('/models/model-{version}').read(432)
            open.assert_called_with('/models/model-432.pkl.gz', 'rb')
            assert result == load.return_value
            load.assert_called_with(gzopen.return_value.__enter__.return_value)

    def test_read_no_model(self, File):
        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.File.list_properties') as lp:
            lp.return_value = {}
            lm.return_value = []
            filename = '/models/model-{version}'
            f = File(filename)
            with pytest.raises(LookupError) as exc:
                f.read()
            assert exc.value.args[0] == 'No active model available: {}'.format(filename)

    def test_read_no_active_model(self, File):
        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.File.list_properties') as lp:
            lp.return_value = {}
            lm.return_value = [{'version': 99}]
            filename = '/models/model-{version}'
            f = File(filename)
            with pytest.raises(LookupError) as exc:
                f.read()
            assert exc.value.args[0] == 'No active model available: {}'.format(filename)

    def test_read_no_model_with_given_version(self, File):
        with patch('palladium.persistence.os.path.exists') as exists:
            exists.return_value = False
            f = File('/models/model-{version}')
            with pytest.raises(LookupError) as exc:
                f.read(1)
            assert exc.value.args[0] == 'No such version: 1'

    def test_write_no_model_files(self, File):
        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.File._update_md') as update_md,\
            patch('palladium.persistence.open') as open,\
            patch('palladium.persistence.gzip.open') as gzopen,\
            patch('palladium.persistence.pickle.dump') as dump:
            lm.return_value = []
            gzopen.return_value = MagicMock()
            model = MagicMock()
            result = File('/models/model-{version}').write(model)
            open.assert_called_with('/models/model-1.pkl.gz', 'wb')
            dump.assert_called_with(
                model,
                gzopen.return_value.__enter__.return_value,
                )
            update_md.assert_called_with({'models': [model.__metadata__]})
            assert result == 1

    def test_write_with_model_files(self, File):
        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.File._update_md') as update_md,\
            patch('palladium.persistence.open') as open,\
            patch('palladium.persistence.gzip.open') as gzopen,\
            patch('palladium.persistence.pickle.dump') as dump:
            lm.return_value = [{'version': 99}]
            gzopen.return_value = MagicMock()
            model = MagicMock()
            result = File('/models/model-{version}').write(model)
            open.assert_called_with('/models/model-100.pkl.gz', 'wb')
            dump.assert_called_with(
                model,
                gzopen.return_value.__enter__.return_value,
                )
            update_md.assert_called_with(
                {'models': [{'version': 99}, model.__metadata__]})
            assert result == 100

    def test_update_metadata(self, File):
        model = MagicMock(__metadata__={
            'existing': 'entry', 'version': 'overwritten'})

        with patch('palladium.persistence.File.list_models') as lm,\
            patch('palladium.persistence.File._update_md') as update_md,\
            patch('palladium.persistence.gzip.open'),\
            patch('palladium.persistence.open'),\
            patch('palladium.persistence.pickle.dump'):
            lm.return_value = [{'version': 99}]
            File('/models/model-{version}').write(model)
            assert model.__metadata__ == {
                'existing': 'entry',
                'version': 100,
                }
            update_md.assert_called_with(
                {'models': [{'version': 99}, model.__metadata__]})

    def test_list_models_no_metadata(self, File):
        with patch('palladium.persistence.os.path.exists') as exists:
            exists.return_value = False
            assert File('model-{version}').list_models() == []
            exists.assert_called_with('model-metadata.json')

    def test_list_models_with_metadata(self, File):
        with patch('palladium.persistence.File._read_md') as read_md:
            read_md.return_value = {'models': [{'version': 99}]}
            assert File('model-{version}').list_models() == [{'version': 99}]

    def test_list_properties_no_metadata(self, File):
        from palladium import __version__
        with patch('palladium.persistence.os.path.exists') as exists:
            exists.return_value = False
            assert File('model-{version}').list_properties() == {
                'db-version': __version__,
                }
            exists.assert_called_with('model-metadata.json')

    def test_list_properties_with_metadata(self, File):
        with patch('palladium.persistence.File._read_md') as read_md:
            read_md.return_value = {
                'properties': {
                    'active-model': '33',
                    'hello': 'world',
                    },
                }
            assert File('model-{version}').list_properties() == {
                'active-model': '33', 'hello': 'world',
                }

    def test_update_md(self, File):
        with patch('palladium.persistence.File._read_md') as read_md,\
            patch('builtins.open') as open:
            read_md.return_value = {
                'hello': 'world',
                'models': [1],
                'properties': {},
                }
            File('model-{version}')._update_md_orig({'models': [2]})
            open.assert_called_with('model-metadata.json', 'wb')
            fh = open.return_value.__enter__.return_value
            json_written = json.loads(fh.write.call_args[0][0].decode('utf-8'))
            assert json_written == {
                'hello': 'world',
                'models': [2],
                'properties': {},
                }

    def test_read_md(self, File):
        with patch('builtins.open') as open,\
             patch('palladium.persistence.os.path.exists') as exists,\
             patch('palladium.persistence.json.load') as load:
            exists.return_value = True
            result = File('model-{version}')._read_md()
            exists.assert_called_with('model-metadata.json')
            open.assert_called_with('model-metadata.json', 'r')
            load.assert_called_with(
                open.return_value.__enter__.return_value,
                )
            assert result == load.return_value

    def test_read_md_no_file(self, File):
        from palladium import __version__
        with patch('palladium.persistence.os.path.exists') as exists:
            exists.return_value = False
            assert File('model-{version}')._read_md() == {
                'models': [],
                'properties': {'db-version': __version__},
                }

    def test_activate(self, File):
        with patch('palladium.persistence.File._read_md') as read_md,\
             patch('palladium.persistence.File._update_md') as update_md:
            read_md.return_value = {
                'models': [{'version': 1}, {'version': 2}],
                'properties': {'active-model': '2'},
                }
            File('model-{version}').activate(1)
            update_md.assert_called_with({
                'properties': {'active-model': '1'},
                })

    def test_activate_bad_version(self, File):
        with patch('palladium.persistence.File._read_md') as read_md,\
             patch('palladium.persistence.File._update_md') as update_md:
            read_md.return_value = {
                'models': [{'version': 1}, {'version': 2}],
                'properties': {'active-model': '2'},
                }
            with pytest.raises(LookupError) as exc:
                File('model-{version}').activate(3)
            assert exc.value.args[0] == 'No such version: 3'

    def test_read_activated_model_missing(self, File):
        with patch('palladium.persistence.File._read_md') as read_md,\
             patch('palladium.persistence.File._update_md') as update_md:
            read_md.return_value = {
                'models': [{'version': 1}, {'version': 3}],
                'properties': {'active-model': '2'},
                }
            with pytest.raises(LookupError) as exc:
                File('model-{version}').read()
            assert (exc.value.args[0] ==
                    'Activated model not available. Maybe it was deleted.')

    def test_delete(self, File):
        with patch('palladium.persistence.File._read_md') as read_md,\
             patch('palladium.persistence.File._update_md') as update_md,\
             patch('palladium.persistence.os') as os:
            read_md.return_value = {
                'models': [{'version': 1}, {'version': 2}],
                'properties': {'active-model': '2'},
                }
            File('model-{version}').delete(1)
            update_md.assert_called_with({
                'models': [{'version': 2}],
                })
            os.remove.assert_called_with('model-1.pkl.gz')

    def test_delete_bad_version(self, File):
        with patch('palladium.persistence.File._read_md') as read_md,\
             patch('palladium.persistence.File._update_md') as update_md,\
             patch('palladium.persistence.os') as os:
            read_md.return_value = {
                'models': [{'version': 1}, {'version': 2}],
                'properties': {'active-model': '2'},
                }
            with pytest.raises(LookupError) as exc:
                File('model-{version}').delete(3)
            assert exc.value.args[0] == 'No such version: 3'

    def test_upgrade_no_args(self, File):
        from palladium import __version__

        persister = File('model-{version}')
        with patch.object(File, '_read_md',
                          return_value={'properties': {'db-version': '0.33'}}):
            with patch.object(File, 'upgrade_steps') as upgrade_steps:
                persister.upgrade()
        upgrade_steps.run.assert_called_with(persister, '0.33', __version__)
        assert persister.list_properties()['db-version'] == __version__

    def test_upgrade_with_legacy_md(self, File):
        from palladium import __version__

        persister = File('model-{version}')
        legacy_md = [{'some': 'model'}]
        with patch.object(File, '_read_md',
                          side_effect=[legacy_md, {'properties': {}}]):
            with patch.object(File, 'upgrade_steps') as upgrade_steps:
                persister.upgrade()
        upgrade_steps.run.assert_called_with(persister, '0.0', __version__)
        assert persister.list_properties()['db-version'] == __version__

    def test_upgrade_from_version(self, File):
        from palladium import __version__

        persister = File('model-{version}')
        with patch.object(File, 'upgrade_steps') as upgrade_steps:
            persister.upgrade(from_version='0.34')
        upgrade_steps.run.assert_called_with(persister, '0.34', __version__)
        assert persister.list_properties()['db-version'] == __version__

    def test_upgrade_1_0(self, File):
        with patch('builtins.open') as open,\
            patch('palladium.persistence.os.path.exists') as exists,\
            patch('palladium.persistence.json.load') as load,\
            patch('palladium.persistence.json.dump') as dump:

            exists.return_value = True
            load.side_effect = [
                [{'version': '1'}, {'version': '2'}],
                {'properties': {}},
                ]
            File('model-{version}').upgrade(
                from_version="0.0", to_version="1.0")
            exists.assert_called_with('model-metadata.json')
            open_rv = open.return_value.__enter__.return_value
            load.assert_called_with(open_rv)
            new_md = {
                'models': [{'version': '1'}, {'version': '2'}],
                'properties': {
                    'active-model': '2',
                    },
                }
            dump.assert_called_with(new_md, open_rv, indent=4)

    def test_upgrade_1_0_no_metadata(self, File):
        with patch('builtins.open') as open,\
            patch('palladium.persistence.os.path.exists') as exists,\
            patch('palladium.persistence.json.dump') as dump:

            exists.return_value = False
            File('model-{version}').upgrade(
                from_version="0.0", to_version="1.0")
            exists.assert_called_with('model-metadata.json')
            open_rv = open.return_value.__enter__.return_value
            new_md = {'models': [], 'properties': {}}
            dump.assert_called_with(new_md, open_rv, indent=4)


class TestFileAttachments:
    @pytest.fixture
    def persister(self, tmpdir):
        from palladium.persistence import File
        model1 = Dummy()
        annotate(model1, {'attachments/myatt.txt': 'aGV5',
                          'attachments/my2ndatt.txt': 'aG8='})
        model2 = Dummy()
        annotate(model2, {'attachments/myatt.txt': 'aG8='})
        persister = File(str(tmpdir) + '/model-{version}')
        persister.write(model1)
        persister.write(model2)
        return persister

    def test_filenames(self, persister, tmpdir):
        # Attachment files are namespaced by the model:
        assert sorted(os.listdir(tmpdir)) == [
            'model-1-my2ndatt.txt', 'model-1-myatt.txt', 'model-1.pkl.gz',
            'model-2-myatt.txt', 'model-2.pkl.gz',
            'model-metadata.json',
            ]

    def test_attachment_file_contents(self, persister, tmpdir):
        # Attachment data is written to files system decoded:
        with open(tmpdir + '/model-1-myatt.txt', 'rb') as f:
            assert f.read() == b'hey'
        with open(tmpdir + '/model-1-my2ndatt.txt', 'rb') as f:
            assert f.read() == b'ho'
        with open(tmpdir + '/model-2-myatt.txt', 'rb') as f:
            assert f.read() == b'ho'

    def test_attachment_not_in_metadata_file(self, persister, tmpdir):
        # Attachment data is not written to the metadata file:
        with open(tmpdir + '/model-metadata.json') as f:
            md = json.loads(f.read())
            assert len(md['models']) == 2
            for model_md in md['models']:
                assert 'attachments/myatt.txt' not in model_md

    def test_attachment_not_in_pickle(self, persister, tmpdir):
        # Attachment data is not pickled as part of the model:
        with open(tmpdir + '/model-1.pkl.gz', 'rb') as fh:
            with gzip.open(fh, 'rb') as f:
                model1 = pickle.load(f)
                assert 'attachments/myatt.txt' not in annotate(model1)

    def test_loaded_back_on_read(self, persister, tmpdir):
        # Attachment is read back from the file into metadata
        # dictionary on read:
        model1 = persister.read(version=1)
        assert annotate(model1)['attachments/myatt.txt'] == b'aGV5'
        assert annotate(model1)['attachments/my2ndatt.txt'] == b'aG8='

    def test_deleted_on_delete(self, persister, tmpdir):
        # Attachment files are removed from the file system when a
        # model is deleted:
        persister.delete(1)
        assert sorted(os.listdir(tmpdir)) == [
            'model-2-myatt.txt', 'model-2.pkl.gz',
            'model-metadata.json',
            ]


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

    def test_initialize_properties(self, database):
        from palladium import __version__
        assert database.list_properties() == {'db-version': __version__}

    def test_read(self, database, dbmodel):
        database.write(Dummy(name='mymodel'))
        database.activate(1)
        assert database.read() == dbmodel

    def test_read_with_version(self, database, dbmodel):
        database.write(Dummy(name='mymodel'))
        assert database.read(1) == dbmodel

    def test_read_no_model(self, database):
        with pytest.raises(LookupError) as exc:
            database.read()
        assert exc.value.args[0] == 'No model available'

    def test_read_no_active_model(self, database, dbmodel):
        with pytest.raises(LookupError) as exc:
            database.read()
        assert exc.value.args[0] == 'No model available'

    def test_read_activated_model_missing(self, database, dbmodel):
        database.write(Dummy(name='mymodel'))
        database.write(Dummy(name='mymodel2'))
        database.activate(2)
        database.delete(2)
        with pytest.raises(LookupError) as exc:
            database.read()
        assert (exc.value.args[0] ==
                'Activated model not available. Maybe it was deleted.')

    def test_activate(self, database, dbmodel):
        assert 'active-model' not in database.list_properties()
        database.activate(1)
        assert database.list_properties()['active-model'] == '1'

    def test_delete(self, database, dbmodel):
        model = Dummy(name='mymodel')
        database.write(model)
        assert [m['version'] for m in database.list_models()] == [1, 2]
        assert database.read(2) == model
        database.delete(2)
        assert [m['version'] for m in database.list_models()] == [1]
        with pytest.raises(LookupError) as exc:
            database.read(2)
        assert exc.value.args[0] == 'No model available'

    def test_write_no_entry(self, database):
        model = Dummy(name='mymodel')
        database.activate(database.write(model))
        assert database.read() == model
        assert model.__metadata__['version'] == 1

    def test_write_with_existing_entry(self, database, dbmodel):
        model = Dummy(name='mymodel')
        database.activate(database.write(model))
        assert database.read() == model
        assert model.__metadata__['version'] == 2
        assert database.read(1) == dbmodel

    def test_concurrent_read_write(self, database, dbmodel):
        database.activate(1)
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
                version = database.write(model)
                database.activate(version)
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

    def test_list_models_no_entries(self, database):
        assert database.list_models() == []

    def test_list_models_with_existing_entry(self, database, dbmodel):
        listing = database.list_models()
        assert listing == [dbmodel.__metadata__]

    def test_list_models_with_two_entries(self, database, dbmodel):
        model2 = Dummy(name='mymodel')
        database.write(model2)
        listing = database.list_models()
        assert listing == [dbmodel.__metadata__, model2.__metadata__]

    def test_upgrade_no_args(self, database):
        from palladium import __version__

        with patch.object(database, 'list_properties',
                          return_value={'db-version': '0.33'}):
            with patch.object(database, 'upgrade_steps') as upgrade_steps:
                database.upgrade()
        upgrade_steps.run.assert_called_with(database, '0.33', __version__)
        assert database.list_properties()['db-version'] == __version__

    def test_upgrade_from_version(self, database):
        from palladium import __version__

        with patch.object(database, 'upgrade_steps') as upgrade_steps:
            database.upgrade(from_version='0.34')
        upgrade_steps.run.assert_called_with(database, '0.34', __version__)
        assert database.list_properties()['db-version'] == __version__

    def test_upgrade_1_0(self, database, dbmodel):
        from palladium import __version__

        model2 = Dummy(name='mymodel')
        database.write(model2)
        assert database.list_properties() == {
            'db-version': __version__}
        database.upgrade(from_version='0.0', to_version='1.0')
        assert database.list_properties() == {
            'db-version': '1.0', 'active-model': '2'}

    def test_table_postfix_default(self, Database, request):
        path = '/tmp/palladium.testing-{}.sqlite'.format(os.getpid())
        request.addfinalizer(lambda: os.remove(path))
        db = Database('sqlite:///{}'.format(path))
        assert db.Property.__tablename__ == 'properties'
        assert db.DBModel.__tablename__ == 'models'
        assert db.DBModelChunk.__tablename__ == 'model_chunks'

    def test_table_postfix(self, Database, request):
        path = '/tmp/palladium.testing-{}.sqlite'.format(os.getpid())
        request.addfinalizer(lambda: os.remove(path))
        db = Database('sqlite:///{}'.format(path), table_postfix='fix')
        assert db.Property.__tablename__ == 'properties_fix'
        assert db.DBModel.__tablename__ == 'models_fix'
        assert db.DBModelChunk.__tablename__ == 'model_chunks_fix'

    def test_init_poolclass_default(self, Database, request):
        from sqlalchemy.pool import NullPool
        path = '/tmp/palladium.testing-{}.sqlite'.format(os.getpid())
        request.addfinalizer(lambda: os.remove(path))
        db = Database('sqlite:///{}'.format(path))
        assert isinstance(db.engine.pool, NullPool)

    def test_init_poolclass_set(self, Database, request):
        from sqlalchemy.pool import QueuePool
        path = '/tmp/palladium.testing-{}.sqlite'.format(os.getpid())
        request.addfinalizer(lambda: os.remove(path))
        db = Database('sqlite:///{}'.format(path), poolclass=QueuePool)
        assert isinstance(db.engine.pool, QueuePool)


@pytest.fixture
def mocked_requests():
    with requests_mock.Mocker() as m:
        yield m


class TestRest:
    base_url = "https://some.restyfactory.wtf/repo"

    @pytest.fixture
    def persister(self):
        from palladium.persistence import Rest
        return Rest(
            "%s/mymodel-{version}" % (self.base_url,),
            auth=("the_user", "the_pass"),
            )

    def assert_auth_headers(self, mocked_requests):
        encoded = codecs.encode(b'the_user:the_pass', 'base64').strip()
        auth_header = 'Basic %s' % (encoded.decode('ascii'),)
        for req in mocked_requests.request_history:
            assert req.headers['Authorization'] == auth_header

    def test_upload(self, mocked_requests, persister):
        """ test upload of model and metadata """
        model = Dummy(name='mymodel')

        get_md_url = "%s/mymodel-metadata.json" % (self.base_url,)
        mocked_requests.head(get_md_url, status_code=404)

        put_model_body = None
        def handle_put_model(request, context):
            nonlocal put_model_body
            put_model_body = request.body.read()
            return ''

        put_model_url = "%s/mymodel-1.pkl.gz" % (self.base_url,)
        put_model = mocked_requests.put(
            put_model_url,
            text=handle_put_model,
            status_code=201,
            )

        put_md_body = None
        def handle_put_md(request, context):
            nonlocal put_md_body
            put_md_body = request.body.read()
            return ''

        put_md_url = "%s/mymodel-metadata.json" % (self.base_url,)
        put_md = mocked_requests.put(
            put_md_url,
            text=handle_put_md,
            status_code=201,
            )

        persister.write(model)
        assert put_model.called
        assert put_md.called

        assert pickle.loads(gzip.decompress(put_model_body)) == model
        assert len(json.loads(put_md_body.decode('utf-8'))['models']) == 1
        self.assert_auth_headers(mocked_requests)

    def test_download(self, mocked_requests, persister):
        """ test download and activation of a model """
        expected = Dummy(name='mymodel', __metadata__={})
        zipped_model = gzip.compress(pickle.dumps(expected))

        get_md_url = "%s/mymodel-metadata.json" % (self.base_url,)
        mocked_requests.head(get_md_url, status_code=200)
        get_md = mocked_requests.get(
            get_md_url,
            json={"models": [{"version": 1}],
                  "properties": {'active-model': 1}},
            status_code=200,
            )

        get_model_url = "%s/mymodel-1.pkl.gz" % (self.base_url,)
        mocked_requests.head(get_model_url, status_code=200)
        get_model = mocked_requests.get(
            get_model_url,
            content=zipped_model,
            status_code=200,
            )

        model = persister.read()
        assert get_md.called
        assert get_model.called
        assert model == expected
        self.assert_auth_headers(mocked_requests)

    def test_delete(self, mocked_requests, persister):
        """ test deleting a model and metadata update """

        get_md_url = "%s/mymodel-metadata.json" % (self.base_url,)
        mocked_requests.head(get_md_url, status_code=200)
        mocked_requests.get(
            get_md_url,
            json={"models": [{"version": 1}],
                  "properties": {'active-model': 1}},
            status_code=200,
            )

        put_md_body = None
        def handle_put_md(request, context):
            nonlocal put_md_body
            put_md_body = request.body.read()
            return ''

        put_md_url = "%s/mymodel-metadata.json" % (self.base_url,)
        put_md = mocked_requests.put(
            put_md_url,
            text=handle_put_md,
            status_code=201,
            )

        delete_model_url = "%s/mymodel-1.pkl.gz" % (self.base_url,)
        delete_model = mocked_requests.delete(
            delete_model_url,
            status_code=200,
            )

        persister.delete(1)
        assert put_md.called
        assert delete_model.called
        assert len(json.loads(put_md_body.decode('utf-8'))['models']) == 0
        self.assert_auth_headers(mocked_requests)


class TestRestIO:
    @pytest.fixture
    def io(self):
        from palladium.persistence import RestIO
        return RestIO(('auth', 'aut'))

    def test_unsupported_filemode(self, io):
        with pytest.raises(NotImplementedError):
            io.open('haha', mode='a')


class TestDatabaseCLOB(TestDatabase):
    @pytest.fixture
    def Database(self):
        from palladium.persistence import DatabaseCLOB
        return DatabaseCLOB


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
        persister.__pld_config_key__ = 'myname'
        process_store['myname'] = 'mymodel'
        assert persister.read() == 'mymodel'

    def test_write(self, persister):
        persister.write('mymodel')
        persister.impl.write.assert_called_with('mymodel')

    def test_update_cache(self, persister):
        persister.update_cache()
        assert persister.read() is persister.impl.read.return_value
        persister.impl.read.assert_called_with()
        assert len(persister.impl.read.mock_calls) == 1

    def test_update_cache_no_check_version(self, persister):
        persister.check_version = False
        persister.update_cache()
        assert persister.read() is persister.impl.read.return_value
        persister.impl.read.assert_called_with()
        assert len(persister.impl.read.mock_calls) == 2

    def test_update_cache_specific_version(self, persister):
        persister.update_cache(version=123)
        assert persister.read() is persister.impl.read.return_value
        persister.impl.read.assert_called_with(version=123)
        assert len(persister.impl.read.mock_calls) == 2

    def test_update_cache_rrule(self, process_store, CachedUpdatePersister,
                                config):
        rrule_info = {
            'freq': 'DAILY',
            'dtstart': '2014-10-30T13:21:18',
            }

        impl = MagicMock()
        persister = CachedUpdatePersister(impl, update_cache_rrule=rrule_info)
        persister.__pld_config_key__ = 'mypersister'
        persister.initialize_component(config)
        assert persister.read() is impl.read.return_value
        assert process_store['mypersister'] is impl.read.return_value
        assert impl.read.call_count == 1

    def test_update_cache_lookup_error(self, persister, process_store):
        persister.impl.read.side_effect = LookupError
        persister.__pld_config_key__ = 'thypersister'
        persister.check_version = False
        assert persister.update_cache() is None
        assert 'thypersister' not in process_store

    def test_dont_cache(self, process_store, CachedUpdatePersister, config):
        config['__mode__'] = 'fit'

        rrule_info = {
            'freq': 'DAILY',
            'dtstart': '2014-10-30T13:21:18',
            }

        len_before = len(process_store)
        impl = MagicMock()
        persister = CachedUpdatePersister(impl, update_cache_rrule=rrule_info)
        persister.initialize_component(config)
        assert persister.read() is impl.read.return_value
        assert len(process_store) == len_before
        assert persister.thread is None

    def test_proxy_list_models(self, CachedUpdatePersister):
        impl = Mock()
        persister = CachedUpdatePersister(impl)
        assert persister.list_models() is impl.list_models.return_value

    def test_proxy_list_properties(self, CachedUpdatePersister):
        impl = Mock()
        persister = CachedUpdatePersister(impl)
        assert persister.list_properties() is impl.list_properties.return_value

    def test_proxy_activate(self, CachedUpdatePersister):
        impl = Mock()
        persister = CachedUpdatePersister(impl)
        assert persister.activate(2) is impl.activate.return_value
        impl.activate.assert_called_with(2)

    def test_proxy_delete(self, CachedUpdatePersister):
        impl = Mock()
        persister = CachedUpdatePersister(impl)
        assert persister.delete(2) is impl.delete.return_value
        impl.delete.assert_called_with(2)

    def test_proxy_upgrade(self, CachedUpdatePersister):
        impl = Mock()
        persister = CachedUpdatePersister(impl)
        assert persister.upgrade("0.9", "1.0") is impl.upgrade.return_value
        impl.upgrade.assert_called_with("0.9", "1.0")


@pytest.mark.skip(reason="moto3 error")
class TestS3IO:
    @pytest.fixture
    def test_model_cls(self):
        class TestModel:
            def __init__(self, name, value):
                self.name = name
                self.value = str(value)
        return TestModel

    @pytest.fixture
    def test_models(self, test_model_cls):
        return [test_model_cls(f"model_{n}", n) for n in range(3)]

    @pytest.fixture
    def bucket_name(self):
        return 'test-bucket'

    @pytest.fixture
    def bucket_location(self):
        return 'eu-west-1'

    @pytest.yield_fixture
    def s3_io_filled(self, bucket_name, test_models, bucket_location, s3_io_cls):
        import moto, boto3
        with moto.mock_s3():
            conn = boto3.resource('s3')
            location = {'LocationConstraint': bucket_location}
            conn.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)

            s3 = boto3.client('s3')
            for model in test_models:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=model.name,
                    Body=model.value,
                )

            yield s3_io_cls()

    @pytest.fixture
    def s3_io_cls(self):
        from palladium.persistence import S3IO
        return S3IO

    def test_open(self, s3_io_filled, test_models, bucket_name):
        for expected_model in test_models:
            print(s3_io_filled)
            obj = s3_io_filled.open(posixpath.join(
                bucket_name,
                expected_model.name,
            ))
            print(obj.read())

            assert obj.read() == expected_model.value

    def test_exists(self, s3_io_filled, test_models, bucket_name):
        for expected_model in test_models:
            assert s3_io_filled.exists(posixpath.join(
                bucket_name,
                expected_model.name,
            ))

    def test_remove(self, s3_io_filled, test_models, bucket_name):
        s3_io_filled.remove(posixpath.join(
            bucket_name,
            test_models[0].name,
        ))

        assert not s3_io_filled.exists(posixpath.join(
            bucket_name,
            test_models[0].name,
        ))

        for expected_model in test_models[1:]:
            assert s3_io_filled.exists(posixpath.join(
                bucket_name,
                expected_model.name,
            ))


@pytest.mark.skip(reason="moto3 error")
class TestS3:
    @pytest.fixture
    def s3_cls(self):
        from palladium.persistence import S3
        return S3

    @pytest.fixture
    def bucket_location(self):
        return 'eu-west-1'

    @pytest.yield_fixture
    def s3_cls_with_bucket(self, bucket_name, s3_cls, bucket_location):
        import moto, boto3
        with moto.mock_s3():
            conn = boto3.resource('s3')
            location = {'LocationConstraint': bucket_location}
            conn.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)

            yield s3_cls

    @pytest.fixture
    def bucket_name(self):
        return 'test-bucket'

    @pytest.fixture
    def dummy_model(self):
        return Dummy(weight=3)

    def test_write_read(self, dummy_model, bucket_name, s3_cls_with_bucket):
        persister = s3_cls_with_bucket(posixpath.join(
            bucket_name,
            'mymodel-single-{version}',
        ))
        persister.write(dummy_model)

        assert persister.io.exists(posixpath.join(
            bucket_name,
            'mymodel-single-1.pkl.gz',
        ))

        assert persister.io.exists(posixpath.join(
            bucket_name,
            'mymodel-single-metadata.json',
        ))

        model = persister.read(version=1)
        assert type(model) == type(dummy_model)

    def test_successive_writes(self, dummy_model, bucket_name, s3_cls_with_bucket):
        # NOTE: using the same file spec as with `test_write_read` fails,
        # probably due to some internal inconsistency in moto.
        persister = s3_cls_with_bucket(posixpath.join(
            bucket_name,
            'mymodel-successive-{version}',
        ))

        dummy_model_1 = copy.copy(dummy_model)
        dummy_model_1.weight = 8

        dummy_model_2 = copy.copy(dummy_model)
        dummy_model_2.weight = 9

        persister.write(dummy_model_1)
        persister.write(dummy_model_2)

        read_model_1 = persister.read(version=1)
        read_model_2 = persister.read(version=2)

        assert read_model_1.weight == dummy_model_1.weight
        assert read_model_2.weight == dummy_model_2.weight
