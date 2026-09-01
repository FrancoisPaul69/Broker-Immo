"""Orchestration du pipeline domaine (hors persistance) : ParcelleFiche ->
Property qualifiée -> Score.

Ce module factorise ce que `scripts/top100_demo.py` (Phase 1, tout en
mémoire) et `src/ingest.py` (Phase 3, avec écriture en base) ont en
commun : conversion, nettoyage, qualification, résolution propriétaire,
puis scoring. Il ne fait aucun appel réseau ni accès base de données.
"""

from __future__ import annotations

from src import asset_typing, data_cleaning, owner_resolution
from src.adapters import parcelle_fiche_to_property
from src.pappers_types import ParcelleFiche
from src.portfolio import build_owner_portfolios
from src.schemas import Property, Score
from src.scoring import build_score


def fiche_to_qualified_property(fiche: ParcelleFiche, source: str) -> Property:
    """Convertit, nettoie, qualifie (type_actif) et résout le(s)
    propriétaire(s) d'une ParcelleFiche. Ne calcule pas encore le score :
    celui-ci a besoin de l'ensemble des actifs (comparables, portefeuilles)."""
    property_ = parcelle_fiche_to_property(fiche, source=source)
    property_ = data_cleaning.clean_property(property_)
    property_ = owner_resolution.resolve_property_owners(property_)

    qualification = asset_typing.qualify(property_)
    return property_.model_copy(
        update={
            "type_actif": qualification.type_actif,
            "type_actif_confidence": qualification.confidence,
            "type_actif_indices": qualification.indices,
        }
    )


def build_properties(fiches: list[ParcelleFiche], source: str) -> list[Property]:
    return [fiche_to_qualified_property(fiche, source) for fiche in fiches]


def score_properties(properties: list[Property]) -> dict[str, Score]:
    """Calcule le score de chaque actif. Les comparables (prix/m²) et les
    portefeuilles (taille identifiée en base) sont calculés sur l'ensemble
    des actifs fournis."""
    portfolios = build_owner_portfolios(properties)
    return {p.numero_parcelle: build_score(p, peers=properties, portfolios=portfolios) for p in properties}
