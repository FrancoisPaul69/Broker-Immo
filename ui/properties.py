"""Page TOP 100 : classement filtrable des actifs commerciaux / incertains."""

from __future__ import annotations

import streamlit as st

from ui.components import load_dataset


COLONNES_AFFICHEES = [
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
]


def render() -> None:
    st.title("TOP 100 sourcing commercial")

    properties, scores, ranked = load_dataset()

    if not properties:
        st.info("Base vide. Lancez d'abord une ingestion : `python -m src.ingest --code-postal 69002` (mode demo par défaut).")
        return

    if ranked.empty:
        st.info("Aucun actif commercial ou incertain n'a été identifié dans la base.")
        return

    with st.sidebar:
        st.header("Filtres")
        types = st.multiselect(
            "Type d'actif", options=sorted(ranked["type_actif"].unique()), default=list(ranked["type_actif"].unique())
        )
        confiances = st.multiselect(
            "Confiance de qualification",
            options=sorted(ranked["confiance"].unique()),
            default=list(ranked["confiance"].unique()),
        )
        villes = st.multiselect("Ville", options=sorted(ranked["ville"].unique()))

    filtered = ranked[ranked["type_actif"].isin(types) & ranked["confiance"].isin(confiances)]
    if villes:
        filtered = filtered[filtered["ville"].isin(villes)]

    shortlist = filtered.head(100)
    st.caption(f"{len(shortlist)} actif(s) affiché(s) sur {len(filtered)} correspondant(s) aux filtres.")

    if shortlist.empty:
        st.info("Aucun actif ne correspond aux filtres sélectionnés.")
        return

    st.dataframe(shortlist[COLONNES_AFFICHEES], hide_index=True)

    selected = st.selectbox(
        "Sélectionner un actif",
        options=shortlist["numero_parcelle"].tolist(),
        format_func=lambda value: f"#{shortlist.loc[shortlist['numero_parcelle'] == value, 'rank'].iat[0]} - {value}",
    )

    if st.button("Voir la fiche détail →"):
        st.session_state["selected_parcelle"] = selected
        st.switch_page(st.session_state["pages"]["detail"])
