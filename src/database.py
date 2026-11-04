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
    """Engine SQLAlchemy pour l'URL fournie (ou `config.DATABASE_URL`).

    Sur Postgres, impose un `connect_timeout` : sans lui, une connexion
    vers un hôte injoignable bloque indéfiniment, ce qui fige le script
    Streamlit sur son spinner sans la moindre trace dans les logs.
    `pool_pre_ping` évite de réutiliser une connexion coupée entre deux
    requêtes (cas courant avec un Postgres managé qui se met en veille)."""
    url = database_url or config.DATABASE_URL
    if not url.startswith("postgresql") or "connect_timeout" in url:
        return create_engine(url)
    return create_engine(
        url,
        connect_args={"connect_timeout": config.DATABASE_CONNECT_TIMEOUT_SECONDS},
        pool_pre_ping=True,
    )


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
