from __future__ import annotations

import os
from typing import Iterable

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

import config
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


def _database_url_from_secrets() -> str | None:
    """Lit `DATABASE_URL` dans les secrets Streamlit.

    Sur Streamlit Community Cloud, les secrets de premier niveau sont
    aussi exportés en variables d'environnement, donc `config` les voit
    déjà. Ce repli couvre le cas où ce n'est pas vrai (secret imbriqué,
    version de Streamlit différente). Si aucun fichier de secrets
    n'existe, Streamlit lève : on ignore silencieusement."""
    try:
        value = st.secrets.get("DATABASE_URL")
    except Exception:
        return None
    return str(value) if value else None


# ttl : si la base configurée est momentanément injoignable (Neon en
# veille, Postgres redémarré), le repli DEMO ne doit pas rester figé pour
# toute la durée de vie du serveur.
@st.cache_resource(show_spinner=False, ttl=600)
def resolve_database_url() -> tuple[str, str | None]:
    """Choisit la base à LIRE et retourne `(url, avertissement)`.

    Ordre : la base fournie par l'environnement ou les secrets, sinon la
    base DEMO SQLite embarquée dans le dépôt (`config.DEMO_DATABASE_URL`).
    Si la base configurée est injoignable — cas typique d'un déploiement
    Streamlit Cloud dont le secret pointe vers un Postgres fermé — on
    bascule sur la base DEMO en l'annonçant dans l'interface, plutôt que
    de laisser remonter une traceback sur une page vide.

    Aucune ingestion n'est déclenchée ici : la base DEMO est un fichier
    pré-construit par `python -m src.ingest` (CLAUDE.md, section 3.8)."""
    configured = config.DATABASE_URL if config.DATABASE_URL_IS_EXPLICIT else None
    if configured is None:
        from_secrets = _database_url_from_secrets()
        if from_secrets:
            configured = from_secrets
            os.environ.setdefault("DATABASE_URL", from_secrets)

    demo_available = config.DEMO_DATABASE_PATH.exists()

    if configured is None:
        if demo_available:
            return config.DEMO_DATABASE_URL, None
        return config.DATABASE_URL, None

    try:
        with database.get_engine(configured).connect():
            pass
    except SQLAlchemyError as exc:
        if not demo_available:
            raise
        return config.DEMO_DATABASE_URL, (
            "Base de données configurée injoignable — l'interface affiche le jeu "
            f"DEMO embarqué dans le dépôt. Cause : {type(exc).__name__}."
        )
    return configured, None


def load_dataset() -> tuple[list[Property], dict[str, Score], pd.DataFrame]:
    """Lit les actifs et leur dernier score depuis la base (CLAUDE.md,
    section 5 : Streamlit ne lit que la base, aucun appel à
    demo_source/pipeline depuis ui/). Mis en cache pour la session
    Streamlit plutôt que relu à chaque changement de page.

    La base est peuplée par `python -m src.ingest` (jamais par Streamlit
    lui-même) : voir README.md."""
    database_url, _ = resolve_database_url()
    return _load_dataset_from(database_url)


# Le cache est indexé sur l'URL : si `resolve_database_url` bascule entre
# la base configurée et la base DEMO de repli, les données suivent.
@st.cache_data(show_spinner="Chargement depuis la base...")
def _load_dataset_from(database_url: str) -> tuple[list[Property], dict[str, Score], pd.DataFrame]:
    engine = database.get_engine(database_url)
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
