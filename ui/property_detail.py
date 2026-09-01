"""Page fiche détail : score décomposé, explication, indices de qualification.

L'explicabilité du scoring est la priorité n°3 du projet (CLAUDE.md, section
1) : cette page affiche systématiquement le détail critère par critère
(`score.breakdown`), pas seulement les trois sous-totaux.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components import badge_color, load_dataset


def render() -> None:
    st.title("Fiche actif")

    properties, scores, ranked = load_dataset()

    if not properties:
        st.info("Base vide. Lancez d'abord une ingestion : `python -m src.ingest --code-postal 69002` (mode demo par défaut).")
        return

    if ranked.empty:
        st.info("Aucun actif commercial ou incertain n'a été identifié dans la base.")
        return

    options = ranked["numero_parcelle"].tolist()
    default_parcelle = st.session_state.get("selected_parcelle", options[0])
    default_index = options.index(default_parcelle) if default_parcelle in options else 0

    selected = st.selectbox(
        "Actif",
        options=options,
        index=default_index,
        format_func=lambda value: f"#{ranked.loc[ranked['numero_parcelle'] == value, 'rank'].iat[0]} - {value}",
    )
    st.session_state["selected_parcelle"] = selected

    property_ = next(p for p in properties if p.numero_parcelle == selected)
    score = scores[selected]
    row = ranked.loc[ranked["numero_parcelle"] == selected].iloc[0]

    st.subheader(f"{property_.adresse_brute or property_.numero_parcelle} — {property_.ville or property_.code_commune or '-'}")

    left, right = st.columns(2)
    with left:
        st.write(f"Numéro de parcelle : {property_.numero_parcelle}")
        st.badge(property_.type_actif.value, color="blue")
        st.badge(f"confiance qualification : {property_.type_actif_confidence.value}", color=badge_color(property_.type_actif_confidence.value))
        st.write(
            f"Surface bâtie : {property_.surface_bati:.0f} m²" if property_.surface_bati is not None else "Surface bâtie : inconnue"
        )
        if property_.prix_derniere_mutation is not None:
            date_mutation = property_.date_derniere_mutation.isoformat() if property_.date_derniere_mutation else "date inconnue"
            st.write(f"Prix dernière mutation : {property_.prix_derniere_mutation:,.0f} € ({date_mutation})")
        else:
            st.write("Prix dernière mutation : inconnu")

    with right:
        st.write(f"Propriétaire : {row['owner']}")
        st.metric("Score sourcing", f"{score.sourcing_score:.1f} / 100")
        st.write(f"Actif : {score.asset_score:.1f} / 40")
        st.write(f"Propriétaire : {score.owner_score:.1f} / 30")
        st.write(f"Signaux : {score.sell_signal_score:.1f} / 30")

    st.subheader("Détail du score")
    breakdown_df = pd.DataFrame(
        [
            {"Critère": item.critere, "Points": item.points, "Max": item.points_max, "Détail": item.detail}
            for item in score.breakdown
        ]
    )
    st.dataframe(breakdown_df, hide_index=True)

    with st.expander("Pourquoi ce score ? (explication)"):
        st.write(score.explanation)

    with st.expander("Indices de qualification du type d'actif"):
        if property_.type_actif_indices:
            for indice in property_.type_actif_indices:
                st.write(f"- {indice}")
        else:
            st.write("Aucun indice retenu.")

    with st.expander("Propriétaires associés"):
        for ownership in property_.owners:
            st.write(
                f"- {ownership.owner.nom_entreprise or 'Nom inconnu'} "
                f"(SIREN {ownership.owner.siren or 'inconnu'}) — "
                f"confiance {ownership.confidence_score}/100 (fiabilité API : {ownership.fiabilite_api or 'absente'})"
            )
        if not property_.owners:
            st.write("Aucun propriétaire identifié.")

    with st.expander("Occupants"):
        for occupant in property_.occupants:
            st.write(
                f"- {occupant.enseigne or occupant.nom_entreprise or 'Occupant inconnu'} "
                f"(fiabilité : {occupant.fiabilite_appartenance_parcelle or 'absente'})"
            )
        if not property_.occupants:
            st.write("Aucun occupant identifié.")

    with st.expander("Données techniques (payload)"):
        st.json(
            {
                "numero_parcelle": property_.numero_parcelle,
                "code_postal": property_.code_postal,
                "ville": property_.ville,
                "departement": property_.departement,
                "usage_batiment": property_.usage_batiment,
                "nature_batiment": property_.nature_batiment,
                "source": property_.source,
            }
        )
