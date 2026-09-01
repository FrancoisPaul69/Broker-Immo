"""Résolution du type de propriétaire (CLAUDE.md, section 6).

`type_proprietaire` est dérivé de `categorie_juridique` (nomenclature INSEE)
et de `activite_principale` ; la table de correspondance vit dans
`config.py`. Ce module ne fait AUCUNE hypothèse sur l'identité réelle du
propriétaire au-delà de ce que l'API fournit (règle 3) : à défaut de
catégorie juridique connue, le type reste `inconnu`.
"""

from __future__ import annotations

import re

import config
from src.schemas import Owner, Property, TypeProprietaire


def resolve_owner_type(owner: Owner) -> TypeProprietaire:
    categorie = owner.categorie_juridique

    if not categorie:
        # Pas de catégorie juridique et pas de SIREN : cas typique d'un
        # propriétaire personne physique dans le cadastre (les particuliers
        # n'ont pas de SIREN). Sans nom du tout, le type reste inconnu.
        if not owner.siren and owner.nom_entreprise:
            return TypeProprietaire.PERSONNE_PHYSIQUE
        return TypeProprietaire.INCONNU

    mapped = config.CATEGORIE_JURIDIQUE_TO_TYPE_PROPRIETAIRE.get(categorie)
    if mapped == "societe" and owner.activite_principale:
        division = owner.activite_principale.split(".")[0]
        if division in config.NAF_DIVISIONS_FONCIERE:
            return TypeProprietaire.FONCIERE
    if mapped:
        return TypeProprietaire(mapped)

    if categorie.startswith(config.CATEGORIE_JURIDIQUE_PREFIXE_INSTITUTIONNEL):
        return TypeProprietaire.INSTITUTIONNEL
    if categorie[0] in {"5", "6"}:
        # Catégorie de personne morale de droit privé non mappée finement.
        return TypeProprietaire.SOCIETE
    return TypeProprietaire.AUTRE


def normalize_owner_name(nom: str | None) -> str | None:
    """Normalisation pour comparaison/déduplication (espaces, casse)."""
    if not nom:
        return None
    return re.sub(r"\s+", " ", nom).strip().upper()


def resolve_owner(owner: Owner) -> Owner:
    return owner.model_copy(
        update={
            "type_proprietaire": resolve_owner_type(owner),
            "nom_normalise": normalize_owner_name(owner.nom_entreprise),
        }
    )


def resolve_property_owners(property_: Property) -> Property:
    """Applique resolve_owner à chaque propriétaire lié à l'actif."""
    resolved_ownerships = [
        ownership.model_copy(update={"owner": resolve_owner(ownership.owner)}) for ownership in property_.owners
    ]
    return property_.model_copy(update={"owners": resolved_ownerships})
