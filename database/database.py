"""SQLAlchemy + SQLite — conexão e sessão (Indupack)."""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _ROOT / "indupack.db"
DATABASE_URL = f"sqlite:///{_DB_PATH.as_posix()}"


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Cria tabelas se não existirem (import tardio evita ciclo com models)."""
    from database import models  # noqa: F401
    from services.terminais_store import ensure_tablet_sessao_schema

    Base.metadata.create_all(bind=engine)
    ensure_tablet_sessao_schema()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
