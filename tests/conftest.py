import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FLASK_DEBUG"] = "0"

import pytest
from app import app
from database import init_db
from seed import seed_initial, seed_missing_data


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["DATABASE"] = db_path
    app.config["TESTING"] = True

    with app.app_context():
        init_db()
        seed_initial()
        seed_missing_data()

    with app.test_client() as c:
        yield c

    try:
        os.close(db_fd)
    except OSError:
        pass
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _auto_cleanup(client):
    """Each test gets a fresh temp DB — no cleanup needed.
    This fixture exists only to ensure client fixture runs before every test."""
    yield
