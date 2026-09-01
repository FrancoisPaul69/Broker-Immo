"""Regroupement des actifs par propriétaire, DANS NOTRE BASE (CLAUDE.md, 3.4/7).

Ne jamais confondre avec `Owner.portefeuille_api` (portefeuille déclaré par
l'API Pappers) : ce module ne regroupe que les actifs effectivement
ingérés. L'interface doit toujours écrire "N actifs identifiés dans la
base", jamais "détient N actifs".
"""

from __future__ import annotations

from collections import defaultdict

from src.schemas import Owner, Property


def build_owner_portfolios(properties: list[Property]) -> dict[str, list[Property]]:
    """Retourne siren -> liste des actifs de notre base rattachés à ce siren.

    Un propriétaire sans siren (ex: personne physique non identifiée
    précisément, ou donnée absente) n'est jamais regroupé par nom : sans
    identifiant fiable, le regroupement serait une déduction non fondée
    (règle 2/3)."""
    portfolios: dict[str, list[Property]] = defaultdict(list)
    for property_ in properties:
        sirens_deja_comptes: set[str] = set()
        for ownership in property_.owners:
            siren = ownership.owner.siren
            if not siren or siren in sirens_deja_comptes:
                continue
            sirens_deja_comptes.add(siren)
            portfolios[siren].append(property_)
    return portfolios


def taille_portefeuille_identifie(siren: str | None, portfolios: dict[str, list[Property]]) -> int:
    if not siren:
        return 0
    return len(portfolios.get(siren, []))


def owners_by_siren(properties: list[Property]) -> dict[str, Owner]:
    """Une entrée par siren pour l'affichage (fiche propriétaire). En cas de
    plusieurs enregistrements pour le même siren, le premier rencontré est
    conservé (limite connue : pas de fusion de champs entre enregistrements)."""
    result: dict[str, Owner] = {}
    for property_ in properties:
        for ownership in property_.owners:
            siren = ownership.owner.siren
            if siren and siren not in result:
                result[siren] = ownership.owner
    return result
