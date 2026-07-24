import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FLASK_DEBUG"] = "0"

import pytest
from app import app
from database import get_db


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Clear login_attempts before each test to avoid rate-limit flakiness."""
    with app.app_context():
        try:
            db = get_db()
            db.execute("DELETE FROM login_attempts")
            db.commit()
        except Exception:
            pass
    yield
