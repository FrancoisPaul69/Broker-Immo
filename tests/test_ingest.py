import datetime

from sqlalchemy.orm import Session

from src import database, ingest
from src.models import Base, OwnerModel, PropertyModel, ScoreModel
from src.pappers_immo_client import PappersImmoClient
from tests.test_pappers_immo_client import FakeResponse, FakeSession


def make_session() -> Session:
    engine = database.get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return database.get_session_factory(engine)()


def test_run_demo_persiste_les_actifs_et_les_scores():
    session = make_session()

    resume = ingest.run(session, source="demo")

    assert resume["dry_run"] is False
    assert resume["nb_fiches"] > 0
    proprietes = session.query(PropertyModel).all()
    assert len(proprietes) == resume["nb_fiches"]
    scores = session.query(ScoreModel).all()
    assert len(scores) == resume["nb_fiches"]


def test_run_demo_filtre_par_code_postal():
    session = make_session()

    toutes = ingest.run(make_session(), source="demo")
    resume = ingest.run(session, source="demo", code_postal="69003")

    proprietes = session.query(PropertyModel).all()
    assert 0 < resume["nb_fiches"] <= toutes["nb_fiches"]
    assert all(p.code_postal == "69003" for p in proprietes)


def test_run_demo_dry_run_ne_persiste_rien():
    session = make_session()

    resume = ingest.run(session, source="demo", dry_run=True)

    assert resume["nb_fiches"] > 0
    assert session.query(PropertyModel).count() == 0


def test_run_pappers_sans_numero_parcelle_leve_systemexit():
    session = make_session()
    client = PappersImmoClient(api_key="test", session=FakeSession([]))

    try:
        ingest.run(session, source="pappers", client=client)
        assert False, "SystemExit attendu"
    except SystemExit:
        pass


def test_run_pappers_recupere_et_persiste_via_le_client():
    session = make_session()
    payload = {
        "numero": "69386AB0001",
        "commune": "Lyon",
        "codes_postaux": ["69003"],
        "proprietaires": [{"siren": "123456789", "nom_entreprise": "SCI TEST", "categorie_juridique": "6540"}],
    }
    client = PappersImmoClient(api_key="test", session=FakeSession([FakeResponse(200, payload)]))

    resume = ingest.run(session, source="pappers", numeros_parcelle=["69386AB0001"], client=client)

    assert resume["nb_parcelles_a_interroger"] == 1
    # config.DEFAULT_CHAMPS_SUPPLEMENTAIRES : adresse (1) + bounding_box (1) + proprietaires.parcelles (1) = 3.
    assert resume["jetons"] == 3
    propriete = session.query(PropertyModel).filter_by(numero_parcelle="69386AB0001").one()
    assert propriete.ville == "Lyon"
    assert propriete.raw_payload["numero"] == "69386AB0001"
    proprietaire = session.query(OwnerModel).filter_by(siren="123456789").one()
    assert proprietaire.nom_entreprise == "SCI TEST"


def test_run_pappers_dry_run_estime_le_cout_sans_appeler_l_api():
    session = make_session()
    client = PappersImmoClient(api_key="test", session=FakeSession([]))

    resume = ingest.run(session, source="pappers", numeros_parcelle=["69386AB0001", "69386AB0002"], client=client, dry_run=True)

    assert resume["nb_parcelles_a_interroger"] == 2
    assert client.session.calls == []
    assert session.query(PropertyModel).count() == 0


def test_cache_frais_evite_le_reappel_de_l_api():
    session = make_session()
    payload = {"numero": "69386AB0001", "commune": "Lyon", "codes_postaux": ["69003"]}
    client = PappersImmoClient(api_key="test", session=FakeSession([FakeResponse(200, payload)]))

    # Premier run : appelle l'API et persiste.
    ingest.run(session, source="pappers", numeros_parcelle=["69386AB0001"], client=client)
    assert len(client.session.calls) == 1

    # Second run : la parcelle est fraîche en base, ne doit pas réappeler l'API
    # (la fausse session lèverait une IndexError si .get() était rappelé, la liste étant vide).
    resume = ingest.run(session, source="pappers", numeros_parcelle=["69386AB0001"], client=client)

    assert resume["nb_parcelles_a_interroger"] == 0
    assert len(client.session.calls) == 1  # toujours 1 : pas de second appel


def test_cache_expire_reappelle_l_api():
    session = make_session()
    payload = {"numero": "69386AB0001", "commune": "Lyon"}
    client = PappersImmoClient(api_key="test", session=FakeSession([FakeResponse(200, payload), FakeResponse(200, payload)]))

    ingest.run(session, source="pappers", numeros_parcelle=["69386AB0001"], client=client)

    # Force l'expiration du cache en reculant artificiellement updated_at.
    model = session.query(PropertyModel).filter_by(numero_parcelle="69386AB0001").one()
    model.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=100)
    session.commit()

    resume = ingest.run(session, source="pappers", numeros_parcelle=["69386AB0001"], client=client, ttl_days=30)

    assert resume["nb_parcelles_a_interroger"] == 1
    assert len(client.session.calls) == 2
