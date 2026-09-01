from sqlalchemy.orm import Session

from src import database, ingest, repository
from src.models import Base, PropertyModel


def make_session() -> Session:
    engine = database.get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return database.get_session_factory(engine)()


def test_load_properties_round_trip_compte_et_champs_de_base():
    session = make_session()
    ingest.run(session, source="demo", code_postal="69003")

    properties, scores = repository.load_properties(session, code_postal="69003")

    assert len(properties) > 0
    assert len(scores) == len(properties)
    for property_ in properties:
        assert property_.code_postal == "69003"
        assert property_.numero_parcelle in scores


def test_load_properties_reconstruit_les_objets_lies():
    session = make_session()
    ingest.run(session, source="demo")

    properties, scores = repository.load_properties(session)

    avec_proprietaire = [p for p in properties if p.owners]
    assert avec_proprietaire, "le jeu DEMO doit contenir au moins un actif avec propriétaire identifié"
    property_ = avec_proprietaire[0]
    assert property_.owners[0].owner.nom_entreprise is not None

    avec_occupant = [p for p in properties if p.occupants]
    if avec_occupant:
        occupant = avec_occupant[0].occupants[0]
        assert occupant.confidence_score >= 0

    score = next(iter(scores.values()))
    assert score.breakdown, "le score reconstruit doit conserver le détail critère par critère"
    assert score.config_version


def test_load_properties_conserve_nature_batiment():
    """Régression : nature_batiment doit survivre l'aller-retour base
    (colonne ajoutée après coup, voir PROGRESS.md)."""
    session = make_session()
    ingest.run(session, source="demo")

    properties, _ = repository.load_properties(session)

    avec_nature = [p for p in properties if p.nature_batiment is not None]
    assert avec_nature, "au moins un actif du jeu DEMO doit porter une nature_batiment"


def test_load_properties_prend_le_score_le_plus_recent():
    session = make_session()
    ingest.run(session, source="demo", code_postal="69003")
    ingest.run(session, source="demo", code_postal="69003")  # deuxième run -> deuxième ligne de score

    properties, scores = repository.load_properties(session, code_postal="69003")

    numero = properties[0].numero_parcelle
    model = session.query(PropertyModel).filter_by(numero_parcelle=numero).one()

    assert len(model.scores) == 2  # historique : un run = une ligne (voir ingest.persister_property)
    assert scores[numero].calculated_at == max(s.calculated_at for s in model.scores)
