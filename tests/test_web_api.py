"""Contrat de la façade de lecture destinée au frontend React."""
import config
from src.demo_source import generate_demo_parcelles
from src.pipeline import build_properties, score_properties
from src.web_api import build_dataset_payload

def test_dataset_frontend_reutilise_le_domaine_sans_inventer_de_donnees():
    properties = build_properties(generate_demo_parcelles(), source="demo")
    scores = score_properties(properties)
    payload = build_dataset_payload(properties, scores)
    assert payload["demo"] is True
    assert payload["summary"]["total_assets"] == config.DEMO_NB_LOCAUX
    assert payload["summary"]["qualified_assets"] == len(payload["assets"])
    assert len(payload["assets"]) <= 100
    assert [a["rank"] for a in payload["assets"]] == list(range(1, len(payload["assets"]) + 1))
    assert [a["sourcing_score"] for a in payload["assets"]] == sorted([a["sourcing_score"] for a in payload["assets"]], reverse=True)
    first = payload["assets"][0]
    source = next(p for p in properties if p.numero_parcelle == first["numero_parcelle"])
    assert first["prix_derniere_mutation"] == source.prix_derniere_mutation
    assert first["score_breakdown"]
    assert first["score_explanation"] == scores[first["numero_parcelle"]].explanation

def test_dataset_distingue_portefeuille_base_et_portefeuille_api():
    properties = build_properties(generate_demo_parcelles(), source="demo")
    payload = build_dataset_payload(properties, score_properties(properties))
    assert payload["owners"]
    assert all("actifs" in o and "nb_locaux_api" in o and "nb_parcelles_api" in o for o in payload["owners"])
