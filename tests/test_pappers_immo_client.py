import pytest

from src.pappers_immo_client import CreditBudgetExceeded, PappersImmoClient, PappersImmoError
from src.pappers_types import ParcelleSearchParams


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or str(payload)

    def json(self) -> dict:
        return self._payload


class FakeSession:
    """Remplace requests.Session : rejoue une liste de réponses scriptées,
    une par appel .get(), sans jamais toucher le réseau."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "params": params, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_client(responses, **kwargs) -> PappersImmoClient:
    return PappersImmoClient(
        api_key="test-key",
        session=FakeSession(responses),
        max_retries=2,
        retry_backoff_seconds=0,
        **kwargs,
    )


def test_get_parcelle_fiche_succes_parse_la_reponse():
    client = make_client([FakeResponse(200, {"numero": "69386AB0001", "commune": "Lyon"})])

    fiche = client.get_parcelle_fiche("69386AB0001")

    assert fiche.numero == "69386AB0001"
    assert fiche.commune == "Lyon"
    assert client.session.calls[0]["headers"] == {"api-key": "test-key"}


def test_get_parcelle_fiche_erreur_401_ne_retente_pas():
    client = make_client([FakeResponse(401, text="Clé API incorrecte")])

    with pytest.raises(PappersImmoError):
        client.get_parcelle_fiche("69386AB0001")

    assert len(client.session.calls) == 1  # pas de retry sur une erreur permanente


def test_get_parcelle_fiche_retente_puis_reussit_sur_500():
    client = make_client([FakeResponse(500, text="Erreur serveur"), FakeResponse(200, {"numero": "69386AB0001"})])

    fiche = client.get_parcelle_fiche("69386AB0001")

    assert fiche.numero == "69386AB0001"
    assert len(client.session.calls) == 2


def test_get_parcelle_fiche_echoue_apres_epuisement_des_retries():
    client = make_client([FakeResponse(500, text="1"), FakeResponse(500, text="2"), FakeResponse(500, text="3")])

    with pytest.raises(PappersImmoError):
        client.get_parcelle_fiche("69386AB0001")

    assert len(client.session.calls) == 3  # max_retries=2 -> 3 tentatives au total


def test_estimate_cost_somme_les_couts_documentes():
    client = make_client([])
    assert client.estimate_cost(["adresse", "bounding_box"]) == 2
    assert client.estimate_cost(None) == 0


def test_estimate_cost_refuse_tous():
    client = make_client([])
    with pytest.raises(ValueError):
        client.estimate_cost(["tous"])


def test_estimate_cost_refuse_champ_non_documente():
    client = make_client([])
    with pytest.raises(ValueError):
        client.estimate_cost(["champ_invente"])


def test_budget_credits_bloque_avant_l_appel_reseau():
    client = make_client([], max_credits_per_run=0)

    with pytest.raises(CreditBudgetExceeded):
        client.get_parcelle_fiche("69386AB0001", champs_supplementaires=["adresse"])

    assert client.session.calls == []  # aucune requête envoyée


def test_search_parcelles_retourne_le_json_brut_sans_le_parser():
    payload_brut = {"champ_non_documente": True, "resultats_peut_etre": [{"numero": "X"}]}
    client = make_client([FakeResponse(200, payload_brut)])

    resultat = client.search_parcelles(ParcelleSearchParams(code_postal="69002"))

    assert resultat == payload_brut
    assert client.session.calls[0]["params"] == {"code_postal": "69002"}
