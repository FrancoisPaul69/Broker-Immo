"""Point d'entrée Streamlit : routing entre pages (CLAUDE.md, section 5).

Ne fait aucun calcul métier ni appel réseau : chaque page charge le jeu de
données via `ui.components.load_dataset`, qui lit la base (jamais
`demo_source`/`pipeline` directement, section 5 du CLAUDE.md). Le bandeau
"DEMO DATA — NOT REAL" est affiché ici, avant le routage, pour rester
permanent sur toutes les pages tant que la base ne contient QUE des
actifs `source="demo"` — jamais sur des données réellement issues de
l'API Pappers.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui import dashboard, owners, properties, property_detail
from ui.components import is_demo_dataset, load_dataset, resolve_database_url

st.set_page_config(page_title="Broker Immo — Demo", layout="wide")

# La base lue est résolue ici pour afficher un diagnostic lisible plutôt
# qu'une traceback sur une page vide si elle est injoignable (déploiement
# sans secret `DATABASE_URL`, serveur Postgres éteint).
try:
    _database_url, _fallback_notice = resolve_database_url()
    if _fallback_notice:
        st.warning(_fallback_notice)
    _properties, _scores, _ranked = load_dataset()
except SQLAlchemyError as exc:
    st.error(
        "Impossible de lire la base de données.\n\n"
        f"`{type(exc).__name__}` — vérifier la variable d'environnement "
        "`DATABASE_URL` (ou le secret Streamlit du même nom)."
    )
    st.stop()

if not _properties:
    st.error(
        "La base est accessible mais vide. L'interface ne fait que lire la "
        "base : la peupler au préalable avec `python -m src.ingest` "
        "(voir README.md)."
    )
    st.stop()

if is_demo_dataset(_properties):
    st.warning("DEMO DATA — NOT REAL")

pages = {
    "dashboard": st.Page(dashboard.render, title="Vue d'ensemble", icon="📊", url_path="dashboard", default=True),
    "properties": st.Page(properties.render, title="TOP 100", icon="🏢", url_path="top-100"),
    "detail": st.Page(property_detail.render, title="Fiche actif", icon="🔍", url_path="fiche-actif"),
    "owners": st.Page(owners.render, title="Propriétaires", icon="🧾", url_path="proprietaires"),
}
st.session_state["pages"] = pages

navigation = st.navigation(list(pages.values()))
navigation.run()
