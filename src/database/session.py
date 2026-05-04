import warnings
import logging
import sqlite3
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# One SQLite file for the whole app: always next to this module (same path in repo locally and in Docker
# when compose mounts ./src/database → /app/src/database).
_SQLITE_FILE = Path(__file__).resolve().parent / "database.db"


def _sqlite_url_for_file(db_path: Path) -> str:
    """SQLAlchemy SQLite URL for an absolute path (three slashes after sqlite: + absolute path)."""
    return "sqlite:///" + db_path.resolve().as_posix()


_DEFAULT_DB_URL = _sqlite_url_for_file(_SQLITE_FILE)


def _database_url() -> str:
    """
    Prefer DATABASE_URL from the environment when set to a custom value (e.g. Postgres).
    Otherwise use the canonical repo file above.

    Treat legacy Docker-only paths (sqlite:////app/data/database.db) as the same canonical file so
    local `.env` copied from Compose does not silently use a different DB under /app on the host.
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return _DEFAULT_DB_URL
    if "app/data/database.db" in raw.replace("\\", "/"):
        return _DEFAULT_DB_URL
    return raw


DATABASE_URL = _database_url()


def _ensure_sqlite_parent_dir(url_string: str) -> None:
    if not url_string.startswith("sqlite"):
        return
    u = make_url(url_string)
    if not u.database or u.database == ":memory:":
        return
    path = Path(u.database)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(DATABASE_URL)

engine = create_engine(DATABASE_URL, echo=False)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


Session = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
