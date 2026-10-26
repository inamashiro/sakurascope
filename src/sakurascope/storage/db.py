"""Database bootstrap helpers."""

from __future__ import annotations

from pathlib import Path

from sakurascope.storage.schema import Base, make_engine, make_session_factory


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = make_engine(database_url)
        self.SessionLocal = make_session_factory(self.engine)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self):
        return self.SessionLocal()


def sqlite_url_for(path: Path) -> str:
    resolved = path.resolve()
    # SQLAlchemy wants forward slashes on Windows as well.
    return f"sqlite:///{resolved.as_posix()}"


def create_database(db_path: Path) -> Database:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(sqlite_url_for(db_path))
    database.create_all()
    return database
