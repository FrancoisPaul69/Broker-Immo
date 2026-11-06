"""API HTTP de lecture pour le frontend React.

Cette façade ne recalcule rien et n'appelle jamais Pappers : elle lit les
objets du domaine reconstruits par ``src.repository`` depuis la base, comme
l'interface Streamlit.
"""
from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Any, Iterator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import config
from src import database, repository
from src.portfolio import build_owner_portfolios, owners_by_siren
from src.schemas import Property, Score

def resolve_database_url() -> str:
    """Utilise la base configurée, avec repli explicite sur la démo embarquée."""
    configured = config.DATABASE_URL if config.DATABASE_URL_IS_EXPLICIT else None
    if configured:
        try:
            with database.get_engine(configured).connect():
                return configured
        except SQLAlchemyError:
            if not config.DEMO_DATABASE_PATH.exists():
                raise
    return config.DEMO_DATABASE_URL if config.DEMO_DATABASE_PATH.exists() else config.DATABASE_URL

@contextmanager
def dataset_session() -> Iterator[Session]:
    engine = database.get_engine(resolve_database_url())
    session = database.get_session_factory(engine)()
    try:
        yield session
    finally:
        session.close()

def _primary_owner(property_: Property):
    if not property_.owners:
        return None
    return max(property_.owners, key=lambda ownership: ownership.confidence_score).owner

def _asset_row(rank: int, property_: Property, score: Score) -> dict[str, Any]:
    owner = _primary_owner(property_)
    return {
        "id": property_.numero_parcelle, "rank": rank,
        "numero_parcelle": property_.numero_parcelle,
        "adresse_brute": property_.adresse_brute or property_.numero_parcelle,
        "ville": property_.ville or property_.code_commune or "Non renseignée",
        "code_postal": property_.code_postal or "",
        "type_actif": property_.type_actif.value,
        "type_actif_confidence": property_.type_actif_confidence.value,
        "type_actif_indices": property_.type_actif_indices,
        "surface_bati": property_.surface_bati, "contenance": property_.contenance,
        "prix_derniere_mutation": property_.prix_derniere_mutation,
        "date_derniere_mutation": property_.date_derniere_mutation,
        "usage_batiment": property_.usage_batiment,
        "nature_batiment": property_.nature_batiment,
        "asset_score": score.asset_score, "owner_score": score.owner_score,
        "sell_signal_score": score.sell_signal_score,
        "sourcing_score": score.sourcing_score,
        "score_breakdown": [item.model_dump() for item in score.breakdown],
        "score_explanation": score.explanation,
        "owner": owner.nom_entreprise if owner and owner.nom_entreprise else "Propriétaire inconnu",
        "siren": owner.siren if owner and owner.siren else "Non renseigné",
    }

def build_dataset_payload(properties: list[Property], scores: dict[str, Score]) -> dict[str, Any]:
    """Construit le contrat JSON du frontend depuis les objets du domaine."""
    ranked = [p for p in properties if p.type_actif.value in {"commercial", "incertain"} and p.numero_parcelle in scores]
    ranked.sort(key=lambda p: scores[p.numero_parcelle].sourcing_score, reverse=True)
    assets = [_asset_row(rank, p, scores[p.numero_parcelle]) for rank, p in enumerate(ranked, 1)]
    portfolios = build_owner_portfolios(properties)
    owners = [{
        "id": siren, "siren": siren,
        "nom_entreprise": owner.nom_entreprise or "Nom inconnu",
        "type_proprietaire": owner.type_proprietaire.value,
        "nb_locaux_api": owner.nb_locaux_api,
        "nb_parcelles_api": owner.nb_parcelles_api,
        "cessation_activite": 1 if owner.cessation_activite else 0,
        "actifs": len(portfolios.get(siren, [])),
    } for siren, owner in owners_by_siren(properties).items()]
    owners.sort(key=lambda owner: (-owner["actifs"], owner["nom_entreprise"]))
    type_counts: dict[str, int] = {}
    for p in properties:
        type_counts[p.type_actif.value] = type_counts.get(p.type_actif.value, 0) + 1
    confidence_counts: dict[str, int] = {}
    for p in ranked:
        confidence_counts[p.type_actif_confidence.value] = confidence_counts.get(p.type_actif_confidence.value, 0) + 1
    top100 = assets[:100]
    average = round(sum(a["sourcing_score"] for a in top100) / len(top100), 1) if top100 else None
    return {
        "demo": bool(properties) and all(p.source == "demo" for p in properties),
        "summary": {
            "total_assets": len(properties), "qualified_assets": len(assets),
            "priced_assets": sum(p.prix_derniere_mutation is not None for p in properties),
            "top100_average_score": average, "asset_type_counts": type_counts,
            "confidence_counts": confidence_counts,
        },
        "assets": top100, "owners": owners,
    }

def create_app() -> FastAPI:
    app = FastAPI(title="Broker Immo API", version="1.0.0")
    origins = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])
    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}
    @app.get("/api/dataset")
    def dataset() -> dict[str, Any]:
        with dataset_session() as session:
            properties, scores = repository.load_properties(session)
        return build_dataset_payload(properties, scores)
    return app

app = create_app()
