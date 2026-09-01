"""Page d'accueil : vue d'ensemble du jeu de données chargé."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.components import load_dataset


def render() -> None:
    st.title("Vue d'ensemble")

    properties, scores, ranked = load_dataset()

    if not properties:
        st.info("Base vide. Lancez d'abord une ingestion : `python -m src.ingest --code-postal 69002` (mode demo par défaut).")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Actifs générés", len(properties))
    col2.metric("Actifs commerciaux / incertains", len(ranked))
    avec_prix = [p for p in properties if p.prix_derniere_mutation is not None]
    col3.metric("Avec prix de mutation connu", f"{len(avec_prix)} / {len(properties)}")
    top100 = ranked.head(100)
    col4.metric(
        "Score sourcing moyen (top 100)",
        round(top100["sourcing_score"].mean(), 1) if not top100.empty else "-",
    )

    st.subheader("Répartition par type d'actif")
    type_counts = pd.Series([p.type_actif.value for p in properties], name="type_actif")
    type_counts = type_counts.value_counts().rename_axis("type_actif").reset_index(name="nombre")
    st.plotly_chart(px.bar(type_counts, x="type_actif", y="nombre"), width="stretch")

    if not ranked.empty:
        st.subheader("Confiance de qualification (actifs commerciaux / incertains)")
        confidence_counts = ranked["confiance"].value_counts().rename_axis("confiance").reset_index(name="nombre")
        st.plotly_chart(px.pie(confidence_counts, names="confiance", values="nombre"), width="stretch")

        st.subheader("Distribution des scores de sourcing")
        st.plotly_chart(px.histogram(ranked, x="sourcing_score", nbins=20), width="stretch")
    else:
        st.info("Aucun actif commercial ou incertain n'a été identifié dans la base.")
