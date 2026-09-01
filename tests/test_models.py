from src import database
from src.models import Base


def test_create_all_tables_sqlite():
    """Vérifie que le schéma SQLAlchemy est valide en le créant sur une base
    SQLite en mémoire (pas de serveur PostgreSQL dans cet environnement de
    développement, voir CLAUDE.md)."""
    engine = database.get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    table_names = set(Base.metadata.tables.keys())
    assert table_names == {
        "properties",
        "owners",
        "owner_portfolio_api",
        "ownership",
        "occupants",
        "fonds_de_commerce",
        "companies",
        "transactions",
        "permis",
        "scores",
    }
