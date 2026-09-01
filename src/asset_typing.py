"""Qualification "local commercial" par faisceau d'indices (CLAUDE.md, 3.3).

`type_local_vente` (DVF, hérité de la donnée cadastrale) ne permet pas de
distinguer un commerce d'un entrepôt ou d'un local industriel : sa quatrième
valeur, `local_industriel_commercial_ou_assimile`, confond les trois. La
qualification est donc reconstruite à partir de plusieurs indices,
positifs ou négatifs, combinés en un score. La sortie n'est jamais un
booléen : c'est un triplet (type_actif, confiance, indices retenus),
et un actif incertain reste dans la base plutôt que d'être exclu.
"""

from __future__ import annotations

import config
from src.schemas import ConfianceTyping, Occupant, Property, TypeActif


def naf_section(code_naf: str | None) -> str | None:
    """Retourne la section NAF Rev2 (lettre) d'un code NAF (ex: '47.11D' -> 'G').

    Repose sur la division (les deux premiers chiffres du code), selon la
    nomenclature INSEE référencée par l'API Pappers pour code_naf_occupant
    et code_naf_proprietaire.
    """
    if not code_naf:
        return None
    division = code_naf.strip()[:2]
    return config.NAF_DIVISION_TO_SECTION.get(division)


def _occupant_naf_indices(occupants: list[Occupant]) -> tuple[bool, bool]:
    """Retourne (indice_positif, indice_negatif) selon la section NAF des occupants."""
    positif = False
    negatif = False
    for occupant in occupants:
        section = naf_section(occupant.activite_principale_etablissement)
        if section in config.NAF_SECTION_POSITIVE:
            positif = True
        elif section in config.NAF_SECTION_NEGATIVE:
            negatif = True
    return positif, negatif


class QualificationResult:
    def __init__(self, type_actif: TypeActif, confidence: ConfianceTyping, indices: list[str], score: int):
        self.type_actif = type_actif
        self.confidence = confidence
        self.indices = indices
        self.score = score


def qualify(property_: Property) -> QualificationResult:
    """Qualifie un actif comme commercial, industriel/entrepôt, autre, ou incertain."""

    # Filtre de premier niveau : un type_local_vente résidentiel/dépendance
    # exclut d'office le local commercial (donnée DVF fiable sur ce point).
    if property_.type_local_vente and property_.type_local_vente != "local_industriel_commercial_ou_assimile":
        return QualificationResult(
            TypeActif.AUTRE,
            ConfianceTyping.HAUTE,
            [f"type_local_vente={property_.type_local_vente} (résidentiel/dépendance, hors périmètre commercial)"],
            score=0,
        )

    poids = config.ASSET_TYPING_POIDS
    score = 0
    indices: list[str] = []

    if property_.type_local_vente == "local_industriel_commercial_ou_assimile":
        score += poids["type_local_vente_ok"]
        indices.append("type_local_vente=local_industriel_commercial_ou_assimile (DVF)")

    if property_.usage_batiment in config.ASSET_TYPING_USAGE_BATIMENT_POSITIF:
        score += poids["usage_batiment_positif"]
        indices.append(f"usage_batiment={property_.usage_batiment} (indice positif)")
    elif property_.usage_batiment in config.ASSET_TYPING_USAGE_BATIMENT_NEGATIF:
        score += poids["usage_batiment_negatif"]
        indices.append(f"usage_batiment={property_.usage_batiment} (indice négatif)")

    if property_.nature_batiment in config.ASSET_TYPING_NATURE_BATIMENT_POSITIF:
        score += poids["nature_batiment_positif"]
        indices.append(f"nature_batiment={property_.nature_batiment} (indice positif)")
    elif property_.nature_batiment in config.ASSET_TYPING_NATURE_BATIMENT_NEGATIF:
        score += poids["nature_batiment_negatif"]
        indices.append(f"nature_batiment={property_.nature_batiment} (indice négatif)")

    if property_.fonds_de_commerce:
        score += poids["fonds_de_commerce_present"]
        indices.append(f"fonds de commerce présent sur la parcelle ({len(property_.fonds_de_commerce)})")

    naf_positif, naf_negatif = _occupant_naf_indices(property_.occupants)
    if naf_positif:
        score += poids["naf_occupant_positif"]
        indices.append("occupant avec code NAF en section commerce (G) ou hébergement-restauration (I)")
    if naf_negatif:
        score += poids["naf_occupant_negatif"]
        indices.append("occupant avec code NAF en section industrie/construction/transport (C, F, H)")

    if any(occupant.enseigne for occupant in property_.occupants):
        score += poids["enseigne_presente"]
        indices.append("enseigne renseignée sur un occupant")

    if property_.surface_bati is not None and property_.surface_bati <= config.ASSET_TYPING_SURFACE_COMMERCE_MAX_M2:
        score += poids["surface_coherente_commerce"]
        indices.append(f"surface bâtie ({property_.surface_bati:.0f} m²) cohérente avec du commerce de pied d'immeuble")

    if score <= config.ASSET_TYPING_SEUIL_EXCLUSION:
        return QualificationResult(TypeActif.INDUSTRIEL_OU_ENTREPOT, ConfianceTyping.HAUTE, indices, score)
    if score >= config.ASSET_TYPING_SEUIL_HAUTE_CONFIANCE:
        return QualificationResult(TypeActif.COMMERCIAL, ConfianceTyping.HAUTE, indices, score)
    if score >= config.ASSET_TYPING_SEUIL_CONFIANCE_MOYENNE:
        return QualificationResult(TypeActif.COMMERCIAL, ConfianceTyping.MOYENNE, indices, score)
    return QualificationResult(TypeActif.INCERTAIN, ConfianceTyping.FAIBLE, indices, score)
