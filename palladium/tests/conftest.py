from copy import deepcopy
import pytest


@pytest.fixture
def flask_client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def process_store(request):
    from palladium.util import process_store
    orig = deepcopy(process_store)
    yield process_store
    process_store.clear()
    process_store.update(orig)
