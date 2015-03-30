import pytest


@pytest.fixture
def flask_client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def process_store(request):
    from palladium.util import process_store

    orig = process_store.copy()
    process_store.clear()
    request.addfinalizer(
        lambda: (process_store.clear(), process_store.update(orig)))
    return process_store
