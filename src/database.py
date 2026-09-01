"""Session et engine SQLAlchemy (CLAUDE.md, section 3.8 : Postgres = cache).

`get_engine()` accepte une URL explicite (utilisé par les tests, qui
tournent contre SQLite en mémoire faute de serveur Postgres dans cet
environnement — voir CLAUDE.md, section "Environnement d'exécution").
Sans argument, l'URL vient de `config.DATABASE_URL`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

import config


def get_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or config.DATABASE_URL)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
