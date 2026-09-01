"""Page propriétaires.

Distingue explicitement (CLAUDE.md, section 3.4/7) :
- le portefeuille IDENTIFIÉ DANS NOTRE BASE (`portfolio.build_owner_portfolios`) ;
- le portefeuille DÉCLARÉ PAR L'API (`Owner.nb_locaux_api` / `nb_parcelles_api`).

Ces deux nombres ne sont jamais additionnés ni présentés comme une seule
mesure du patrimoine du propriétaire.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.portfolio import build_owner_portfolios, owners_by_siren
from ui.components import load_dataset


def render() -> None:
    st.title("Propriétaires")

    properties, scores, ranked = load_dataset()

    if not properties:
        st.info("Base vide. Lancez d'abord une ingestion : `python -m src.ingest --code-postal 69002` (mode demo par défaut).")
        return

    portfolios = build_owner_portfolios(properties)
    owners = owners_by_siren(properties)

    if not owners:
        st.info("Aucun propriétaire avec SIREN identifié dans la base.")
        return

    st.caption(
        "« Actifs identifiés dans la base » = actifs de notre base rattachés à ce SIREN. "
        "« Portefeuille déclaré par l'API » = patrimoine total déclaré par Pappers Immobilier pour ce "
        "propriétaire (`proprietaires.locaux` / `proprietaires.parcelles`). Les deux ne sont jamais additionnés."
    )

    rows = [
        {
            "siren": siren,
            "nom_entreprise": owner.nom_entreprise or "Nom inconnu",
            "type_proprietaire": owner.type_proprietaire.value,
            "actifs_identifies_base": len(portfolios.get(siren, [])),
            "locaux_declares_api": owner.nb_locaux_api,
            "parcelles_declarees_api": owner.nb_parcelles_api,
            "cessation_activite": bool(owner.cessation_activite),
        }
        for siren, owner in owners.items()
    ]
    df = pd.DataFrame(rows).sort_values("actifs_identifies_base", ascending=False).reset_index(drop=True)

    st.dataframe(df, hide_index=True)

    selected_siren = st.selectbox(
        "Voir le détail d'un propriétaire",
        options=df["siren"].tolist(),
        format_func=lambda siren: f"{siren} — {owners[siren].nom_entreprise or 'Nom inconnu'}",
    )

    owner = owners[selected_siren]
    owner_properties = portfolios.get(selected_siren, [])

    st.subheader(f"{owner.nom_entreprise or 'Nom inconnu'} ({selected_siren})")

    col1, col2, col3 = st.columns(3)
    col1.metric("Actifs identifiés dans la base", len(owner_properties))
    col2.metric("Locaux déclarés par l'API", owner.nb_locaux_api)
    col3.metric("Parcelles déclarées par l'API", owner.nb_parcelles_api)

    st.write(f"Type de propriétaire : {owner.type_proprietaire.value}")
    if owner.cessation_activite:
        st.badge("Société en cessation d'activité (indice potentiel)", color="orange")

    if owner.portefeuille_api:
        with st.expander("Portefeuille déclaré par l'API (détail)"):
            st.dataframe(pd.DataFrame([entry.model_dump() for entry in owner.portefeuille_api]), hide_index=True)

    st.write("Actifs identifiés dans notre base pour ce propriétaire :")
    if owner_properties:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "numero_parcelle": p.numero_parcelle,
                        "adresse": p.adresse_brute or p.numero_parcelle,
                        "ville": p.ville or "-",
                        "type_actif": p.type_actif.value,
                        "sourcing_score": round(scores[p.numero_parcelle].sourcing_score, 1),
                    }
                    for p in owner_properties
                ]
            ),
            hide_index=True,
        )
    else:
        st.write("Aucun autre actif identifié dans la base pour ce propriétaire.")
