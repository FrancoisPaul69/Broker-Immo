"""Génération déterministe des explications de score (CLAUDE.md, section 7).

Le texte est construit par templates à partir de `score_breakdown`, jamais
par un LLM en V1 (une reformulation IA optionnelle, désactivée par défaut,
pourra être ajoutée en Phase 4 sans remplacer ce texte).

Contrainte non négociable : le vocabulaire interdit dans
`config.EXPLANATION_VOCABULAIRE_INTERDIT` ("veut vendre", "est vendeur"...)
ne doit jamais apparaître. `check_no_blacklisted_terms` est appelé à chaque
génération et lève une erreur si un terme interdit est détecté.
"""

from __future__ import annotations

import config
from src.schemas import Property, ScoreBreakdownItem


def check_no_blacklisted_terms(texte: str) -> None:
    texte_lower = texte.lower()
    for terme in config.EXPLANATION_VOCABULAIRE_INTERDIT:
        if terme in texte_lower:
            raise ValueError(f"Terme interdit détecté dans une explication générée : '{terme}'")


def generate_explanation(
    property_: Property,
    breakdown: list[ScoreBreakdownItem],
    sourcing_score: float,
) -> str:
    asset_score = round(sum(i.points for i in breakdown if i.critere in {"Valeur", "Surface", "Prix/m²", "Localisation"}), 1)
    owner_score = round(
        sum(i.points for i in breakdown if i.critere in {"Taille du portefeuille (base)", "Typologie"}), 1
    )
    sell_signal_score = round(sum(i.points for i in breakdown if i.critere in config.SELL_SIGNAL_POIDS), 1)

    phrases = [
        f"Score de sourcing {sourcing_score:.0f}/100 "
        f"(Actif {asset_score:.0f}/{config.ASSET_SCORE_MAX}, "
        f"Propriétaire {owner_score:.0f}/{config.OWNER_SCORE_MAX}, "
        f"Signaux {sell_signal_score:.0f}/{config.SELL_SIGNAL_SCORE_MAX}).",
        f"Type d'actif retenu : {property_.type_actif.value} (confiance {property_.type_actif_confidence.value}).",
    ]

    signaux_declenches = [item.detail for item in breakdown if item.critere in config.SELL_SIGNAL_POIDS and item.points > 0]
    if signaux_declenches:
        phrases.append("Signaux potentiels identifiés : " + " ; ".join(signaux_declenches) + ".")
    else:
        phrases.append("Aucun signal potentiel identifié dans les données disponibles pour l'instant.")

    texte = " ".join(phrases)
    check_no_blacklisted_terms(texte)
    return texte
