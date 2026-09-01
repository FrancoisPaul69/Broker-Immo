from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from src import database, repository
from src.schemas import Property, Score


def build_ranked_rows(properties: list[Property], scores: dict[str, Score]) -> pd.DataFrame:
    """Retourne les lignes triées du TOP 100 pour l'affichage Streamlit."""
    commercial_or_uncertain = [
        p for p in properties if p.type_actif.value in {"commercial", "incertain"}
    ]
    rows: list[dict] = []
    for property_ in commercial_or_uncertain:
        score = scores[property_.numero_parcelle]
        owner = max(property_.owners, key=lambda o: o.confidence_score).owner if property_.owners else None
        rows.append(
            {
                "rank": 0,
                "numero_parcelle": property_.numero_parcelle,
                "adresse": property_.adresse_brute or property_.numero_parcelle,
                "ville": property_.ville or property_.code_commune or "-",
                "type_actif": property_.type_actif.value,
                "confiance": property_.type_actif_confidence.value,
                "owner": owner.nom_entreprise if owner and owner.nom_entreprise else "Propriétaire inconnu",
                "asset_score": round(score.asset_score, 1),
                "owner_score": round(score.owner_score, 1),
                "sell_signal_score": round(score.sell_signal_score, 1),
                "sourcing_score": round(score.sourcing_score, 1),
                "explanation": score.explanation,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "rank",
                "numero_parcelle",
                "adresse",
                "ville",
                "type_actif",
                "confiance",
                "owner",
                "asset_score",
                "owner_score",
                "sell_signal_score",
                "sourcing_score",
                "explanation",
            ]
        )

    df = df.sort_values("sourcing_score", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


def format_score_badge(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 50:
        return "medium"
    return "low"


def shortlist_for_display(df: pd.DataFrame, limit: int = 100) -> pd.DataFrame:
    return df.head(limit).copy()


# Couleurs st.badge pour les niveaux de confiance (haute/moyenne/faible,
# valeurs API section 3.5) et de score (high/medium/low, format_score_badge).
BADGE_COLORS = {
    "haute": "green",
    "high": "green",
    "moyenne": "orange",
    "medium": "orange",
    "faible": "red",
    "low": "red",
}


def badge_color(level: str) -> str:
    return BADGE_COLORS.get(level, "gray")


@st.cache_data(show_spinner="Chargement depuis la base...")
def load_dataset() -> tuple[list[Property], dict[str, Score], pd.DataFrame]:
    """Lit les actifs et leur dernier score depuis la base (CLAUDE.md,
    section 5 : Streamlit ne lit que la base, aucun appel à
    demo_source/pipeline depuis ui/). Mis en cache pour la session
    Streamlit plutôt que relu à chaque changement de page.

    La base est peuplée par `python -m src.ingest` (jamais par Streamlit
    lui-même) : voir README.md."""
    engine = database.get_engine()
    session_factory = database.get_session_factory(engine)
    session = session_factory()
    try:
        properties, scores = repository.load_properties(session)
    finally:
        session.close()

    ranked = build_ranked_rows(properties, scores)
    return properties, scores, ranked


def is_demo_dataset(properties: list[Property]) -> bool:
    """Vrai si l'intégralité des actifs chargés vient du jeu DEMO (pour
    piloter le bandeau "DEMO DATA — NOT REAL", qui ne doit jamais être
    affiché sur des données réellement issues de l'API Pappers)."""
    return bool(properties) and all(p.source == "demo" for p in properties)
