import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FLASK_DEBUG"] = "0"

import pytest
from app import app
from database import init_db
from seed import seed_initial, seed_missing_data


@pytest.fixture(scope="session")
def seeded_db_path():
    production_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bar_adega.db",
    )
    production_db_stat = os.stat(production_db_path)
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    app.config["DATABASE"] = db_path
    app.config["TESTING"] = True
    with app.app_context():
        init_db()
        seed_initial()
        seed_missing_data()
    yield db_path
    production_db_stat_after = os.stat(production_db_path)
    assert production_db_stat_after.st_size == production_db_stat.st_size
    assert production_db_stat_after.st_mtime_ns == production_db_stat.st_mtime_ns, (
        "A suíte de testes alterou o banco de produção"
    )
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(seeded_db_path):
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    shutil.copyfile(seeded_db_path, db_path)
    test_data_dir = tempfile.mkdtemp(prefix="jams-test-")
    backup_dir = os.path.join(test_data_dir, "backups")
    migration_dir = os.path.join(test_data_dir, "migration")
    uploads_dir = os.path.join(test_data_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    import maintenance.backup as maintenance_backup
    import maintenance.audit as maintenance_audit
    import migration.services as migration_services
    original_backup_dir = maintenance_backup.BACKUP_DIR
    original_audit_path = maintenance_audit.AUDIT_DB_PATH
    original_migration_dir = migration_services.UPLOAD_DIR
    maintenance_backup.BACKUP_DIR = backup_dir
    maintenance_audit.AUDIT_DB_PATH = os.path.join(backup_dir, "audit.db")
    migration_services.UPLOAD_DIR = migration_dir
    app.config["DATABASE"] = db_path
    app.config["BACKUP_UPLOADS_DIR"] = uploads_dir
    app.config["TESTING"] = True

    with app.test_client() as c:
        original_open = c.open

        def open_with_csrf(*args, **kwargs):
            method = str(kwargs.get("method", "GET")).upper()
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                with c.session_transaction() as sess:
                    token = sess.get("_csrf_token")
                if token:
                    headers = kwargs.setdefault("headers", {})
                    headers.setdefault("X-CSRF-Token", token)
            return original_open(*args, **kwargs)

        c.open = open_with_csrf
        yield c

    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except OSError:
        pass
    maintenance_backup.BACKUP_DIR = original_backup_dir
    app.config.pop("BACKUP_UPLOADS_DIR", None)
    maintenance_audit.AUDIT_DB_PATH = original_audit_path
    migration_services.UPLOAD_DIR = original_migration_dir
    shutil.rmtree(test_data_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def _auto_cleanup(client):
    """Each test gets a fresh temp DB — no cleanup needed.
    This fixture exists only to ensure client fixture runs before every test."""
    yield
