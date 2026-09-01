"""Scoring pondéré, transparent, piloté par config.py (CLAUDE.md, section 7).

Pas de ML. Chaque critère produit un `ScoreBreakdownItem` (points obtenus,
points max, détail lisible) : c'est ce détail qui rend le score auditable
et qui alimente `explanations.py`.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime

import config
from src.portfolio import taille_portefeuille_identifie
from src.schemas import Ownership, Property, Score, ScoreBreakdownItem


# ---------------------------------------------------------------------------
# Asset Score (40 points)
# ---------------------------------------------------------------------------
def _score_valeur(prix: float | None) -> ScoreBreakdownItem:
    max_points = config.ASSET_SCORE_VALEUR_MAX
    cible_min, cible_max = config.ASSET_VALEUR_CIBLE_MIN, config.ASSET_VALEUR_CIBLE_MAX

    if prix is None:
        return ScoreBreakdownItem(
            critere="Valeur", points=0, points_max=max_points, detail="Prix de dernière mutation inconnu"
        )
    if cible_min <= prix <= cible_max:
        return ScoreBreakdownItem(
            critere="Valeur",
            points=max_points,
            points_max=max_points,
            detail=f"Prix {prix:,.0f} € dans la fourchette cible ({cible_min:,.0f} - {cible_max:,.0f} €)",
        )

    borne_reference = cible_min if prix < cible_min else cible_max
    ratio_ecart = abs(prix - borne_reference) / borne_reference
    points = max(0.0, max_points * (1 - ratio_ecart / config.ASSET_VALEUR_TOLERANCE_RATIO))
    return ScoreBreakdownItem(
        critere="Valeur",
        points=round(points, 1),
        points_max=max_points,
        detail=f"Prix {prix:,.0f} € hors fourchette cible ({cible_min:,.0f} - {cible_max:,.0f} €), écart {ratio_ecart:.0%}",
    )


def _score_surface(surface: float | None) -> ScoreBreakdownItem:
    max_points = config.ASSET_SCORE_SURFACE_MAX
    cible_min, cible_max = config.ASSET_SURFACE_CIBLE_MIN, config.ASSET_SURFACE_CIBLE_MAX

    if surface is None:
        return ScoreBreakdownItem(critere="Surface", points=0, points_max=max_points, detail="Surface bâtie inconnue")
    if cible_min <= surface <= cible_max:
        return ScoreBreakdownItem(
            critere="Surface",
            points=max_points,
            points_max=max_points,
            detail=f"Surface {surface:.0f} m² dans la fourchette cible ({cible_min:.0f} - {cible_max:.0f} m²)",
        )

    borne_reference = cible_min if surface < cible_min else cible_max
    ratio_ecart = abs(surface - borne_reference) / borne_reference
    points = max(0.0, max_points * (1 - ratio_ecart / config.ASSET_SURFACE_TOLERANCE_RATIO))
    return ScoreBreakdownItem(
        critere="Surface",
        points=round(points, 1),
        points_max=max_points,
        detail=f"Surface {surface:.0f} m² hors fourchette cible ({cible_min:.0f} - {cible_max:.0f} m²)",
    )


def _score_prix_m2(property_: Property, peers: list[Property]) -> ScoreBreakdownItem:
    max_points = config.ASSET_SCORE_PRIX_M2_MAX

    if not property_.prix_m2_fiable or property_.prix_m2 is None:
        return ScoreBreakdownItem(
            critere="Prix/m²",
            points=0,
            points_max=max_points,
            detail="Prix/m² indisponible ou non fiable (mutation multi-lots ou prix inconnu)",
        )

    comparables = [
        p.prix_m2
        for p in peers
        if p.numero_parcelle != property_.numero_parcelle
        and p.prix_m2_fiable
        and p.prix_m2 is not None
        and p.code_commune == property_.code_commune
        and p.type_actif == property_.type_actif
    ]
    if len(comparables) < config.ASSET_PRIX_M2_MIN_COMPARABLES:
        return ScoreBreakdownItem(
            critere="Prix/m²",
            points=0,
            points_max=max_points,
            detail=f"Moins de {config.ASSET_PRIX_M2_MIN_COMPARABLES} mutations comparables (même commune, même type) dans la base",
        )

    mediane = statistics.median(comparables)
    if mediane <= 0:
        return ScoreBreakdownItem(critere="Prix/m²", points=0, points_max=max_points, detail="Médiane comparables invalide")

    # ratio > 0 : l'actif est moins cher que ses comparables (décote, positif
    # pour du sourcing d'acquisition). ratio < 0 : plus cher (prime).
    ratio_ecart = (mediane - property_.prix_m2) / mediane
    decote_max = config.ASSET_PRIX_M2_DECOTE_MAX_RATIO
    prime_max = config.ASSET_PRIX_M2_PRIME_MAX_RATIO

    if ratio_ecart >= decote_max:
        points = max_points
    elif ratio_ecart <= -prime_max:
        points = 0.0
    else:
        points = max_points * (ratio_ecart + prime_max) / (decote_max + prime_max)

    return ScoreBreakdownItem(
        critere="Prix/m²",
        points=round(points, 1),
        points_max=max_points,
        detail=f"{property_.prix_m2:,.0f} €/m² vs médiane comparables {mediane:,.0f} €/m² ({ratio_ecart:+.0%})",
    )


def _score_localisation() -> ScoreBreakdownItem:
    max_points = config.ASSET_SCORE_LOCALISATION_MAX
    if config.ASSET_LOCALISATION_DISPONIBLE:
        raise NotImplementedError("Qualification d'emplacement à implémenter (config.ASSET_LOCALISATION_DISPONIBLE=True)")
    return ScoreBreakdownItem(
        critere="Localisation",
        points=0,
        points_max=max_points,
        detail="Donnée de qualité d'emplacement non disponible dans l'API en V1",
    )


def score_asset(property_: Property, peers: list[Property]) -> list[ScoreBreakdownItem]:
    return [
        _score_valeur(property_.prix_derniere_mutation),
        _score_surface(property_.surface_bati),
        _score_prix_m2(property_, peers),
        _score_localisation(),
    ]


# ---------------------------------------------------------------------------
# Owner Score (30 points)
# ---------------------------------------------------------------------------
def select_ownership(property_: Property) -> Ownership | None:
    """Choisit le propriétaire de référence pour le scoring : celui dont
    l'association à la parcelle est la mieux qualifiée. En cas d'indivision
    (plusieurs propriétaires), c'est une simplification documentée de la V1
    plutôt qu'une agrégation multi-propriétaires."""
    if not property_.owners:
        return None
    return max(property_.owners, key=lambda o: o.confidence_score)


def _score_portefeuille(siren: str | None, portfolios: dict[str, list[Property]]) -> ScoreBreakdownItem:
    max_points = config.OWNER_SCORE_PORTEFEUILLE_MAX
    taille = taille_portefeuille_identifie(siren, portfolios)

    if taille == 0:
        return ScoreBreakdownItem(
            critere="Taille du portefeuille (base)", points=0, points_max=max_points, detail="Aucun propriétaire identifié"
        )

    points = 0
    for borne_inf, borne_sup, bareme_points in config.OWNER_PORTEFEUILLE_BAREME:
        if borne_sup is None and taille >= borne_inf:
            points = bareme_points
            break
        if borne_sup is not None and borne_inf <= taille <= borne_sup:
            points = bareme_points
            break

    return ScoreBreakdownItem(
        critere="Taille du portefeuille (base)",
        points=points,
        points_max=max_points,
        detail=f"{taille} actif(s) identifié(s) dans la base pour ce propriétaire",
    )


def _score_typologie(ownership: Ownership | None) -> ScoreBreakdownItem:
    max_points = config.OWNER_SCORE_TYPOLOGIE_MAX
    if ownership is None:
        return ScoreBreakdownItem(critere="Typologie", points=0, points_max=max_points, detail="Aucun propriétaire identifié")

    type_proprietaire = ownership.owner.type_proprietaire.value
    points = config.TYPE_PROPRIETAIRE_COEFFICIENTS.get(type_proprietaire, 0)
    return ScoreBreakdownItem(
        critere="Typologie",
        points=points,
        points_max=max_points,
        detail=f"Type de propriétaire : {type_proprietaire}",
    )


def score_owner(property_: Property, portfolios: dict[str, list[Property]]) -> list[ScoreBreakdownItem]:
    ownership = select_ownership(property_)
    siren = ownership.owner.siren if ownership else None
    return [_score_portefeuille(siren, portfolios), _score_typologie(ownership)]


# ---------------------------------------------------------------------------
# Sell Signal Score (30 points)
# ---------------------------------------------------------------------------
def _signal(cle: str, declenche: bool, detail: str) -> ScoreBreakdownItem:
    points = config.SELL_SIGNAL_POIDS[cle] if declenche else 0
    return ScoreBreakdownItem(critere=cle, points=points, points_max=config.SELL_SIGNAL_POIDS[cle], detail=detail)


def score_sell_signal(
    property_: Property, portfolios: dict[str, list[Property]], reference_date: date | None = None
) -> list[ScoreBreakdownItem]:
    reference_date = reference_date or date.today()
    ownership = select_ownership(property_)
    items: list[ScoreBreakdownItem] = []

    # Ancienneté de la dernière mutation.
    if property_.date_derniere_mutation is not None:
        anciennete_ans = (reference_date - property_.date_derniere_mutation).days / 365.25
        declenche = anciennete_ans >= config.SELL_SIGNAL_MUTATION_ANCIENNE_ANS
        detail = f"Dernière mutation il y a {anciennete_ans:.0f} an(s) (signal potentiel au-delà de {config.SELL_SIGNAL_MUTATION_ANCIENNE_ANS} ans)"
    else:
        declenche = False
        detail = "Date de dernière mutation inconnue"
    items.append(_signal("mutation_ancienne", declenche, detail))

    # Multiplicité des mutations connues sur la parcelle.
    nb_ventes = len(property_.transactions)
    declenche = nb_ventes >= 2
    items.append(
        _signal("mutations_multiples", declenche, f"{nb_ventes} mutation(s) connue(s) sur la parcelle dans la base")
    )

    # Cessions récentes ailleurs dans le portefeuille du même propriétaire.
    declenche = False
    detail = "Aucun propriétaire identifié"
    if ownership and ownership.owner.siren:
        autres = [p for p in portfolios.get(ownership.owner.siren, []) if p.numero_parcelle != property_.numero_parcelle]
        seuil_jours = config.SELL_SIGNAL_CESSION_RECENTE_MOIS * 30.44
        cessions_recentes = [
            p
            for p in autres
            if p.date_derniere_mutation is not None and (reference_date - p.date_derniere_mutation).days <= seuil_jours
        ]
        declenche = len(cessions_recentes) > 0
        detail = (
            f"{len(cessions_recentes)} autre(s) actif(s) du même propriétaire cédé(s) récemment dans la base"
            if declenche
            else "Aucune cession récente ailleurs dans le portefeuille identifié"
        )
    items.append(_signal("cession_recente_portefeuille", declenche, detail))

    # Mutation de fonds de commerce (indice, à qualifier).
    fdc_avec_mutation = [
        f for f in property_.fonds_de_commerce if f.annonce_bodacc is not None or f.precedent_proprietaire is not None
    ]
    declenche = len(fdc_avec_mutation) > 0
    items.append(
        _signal(
            "fonds_de_commerce_cede",
            declenche,
            f"{len(fdc_avec_mutation)} fonds de commerce avec indice de cession (BODACC ou précédent propriétaire)"
            if declenche
            else "Aucun indice de cession de fonds de commerce",
        )
    )

    # Occupant parti / établissement fermé.
    occupants_partis = [o for o in property_.occupants if o.date_sortie_lieux is not None or o.etablissement_ferme]
    declenche = len(occupants_partis) > 0
    items.append(
        _signal(
            "occupant_parti",
            declenche,
            f"{len(occupants_partis)} occupant(s) parti(s) ou établissement fermé (indice de vacance à qualifier)"
            if declenche
            else "Aucun occupant parti identifié",
        )
    )

    # Propriétaire en cessation d'activité.
    declenche = bool(ownership and ownership.owner.cessation_activite)
    items.append(
        _signal(
            "proprietaire_cessation_activite",
            declenche,
            "Propriétaire en cessation d'activité (indice potentiel)" if declenche else "Propriétaire non signalé en cessation d'activité",
        )
    )

    # Permis récent.
    permis_recents = [
        p
        for p in property_.permis
        if p.date_autorisation is not None
        and (reference_date - p.date_autorisation).days <= config.SELL_SIGNAL_PERMIS_RECENT_ANS * 365.25
    ]
    declenche = len(permis_recents) > 0
    items.append(
        _signal(
            "permis_recent",
            declenche,
            f"{len(permis_recents)} permis récent(s) sur la parcelle (indice potentiel de valorisation)"
            if declenche
            else "Aucun permis récent identifié",
        )
    )

    # Taille du portefeuille DÉCLARÉ par l'API (distinct du portefeuille base).
    declenche = False
    detail = "Aucun propriétaire identifié"
    if ownership:
        taille_declaree = max(ownership.owner.nb_parcelles_api, ownership.owner.nb_locaux_api)
        declenche = taille_declaree >= config.SELL_SIGNAL_GROS_PORTEFEUILLE_SEUIL
        detail = f"Portefeuille déclaré par l'API : {taille_declaree} référence(s)"
    items.append(_signal("gros_portefeuille_declare", declenche, detail))

    return items


# ---------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------
def _total(items: list[ScoreBreakdownItem], plafond: float) -> float:
    return min(plafond, round(sum(item.points for item in items), 1))


def compute_scores(
    property_: Property, peers: list[Property], portfolios: dict[str, list[Property]], reference_date: date | None = None
) -> tuple[float, float, float, list[ScoreBreakdownItem]]:
    """Retourne (asset_score, owner_score, sell_signal_score, breakdown complet)."""
    breakdown_asset = score_asset(property_, peers)
    breakdown_owner = score_owner(property_, portfolios)
    breakdown_sell = score_sell_signal(property_, portfolios, reference_date)

    asset_score = _total(breakdown_asset, config.ASSET_SCORE_MAX)
    owner_score = _total(breakdown_owner, config.OWNER_SCORE_MAX)
    sell_signal_score = _total(breakdown_sell, config.SELL_SIGNAL_SCORE_MAX)

    return asset_score, owner_score, sell_signal_score, breakdown_asset + breakdown_owner + breakdown_sell


def build_score(
    property_: Property, peers: list[Property], portfolios: dict[str, list[Property]], reference_date: date | None = None
) -> Score:
    from src import explanations  # import tardif pour éviter un cycle de modules

    asset_score, owner_score, sell_signal_score, breakdown = compute_scores(property_, peers, portfolios, reference_date)
    sourcing_score = round(asset_score + owner_score + sell_signal_score, 1)
    explanation = explanations.generate_explanation(property_, breakdown, sourcing_score)

    return Score(
        numero_parcelle=property_.numero_parcelle,
        asset_score=asset_score,
        owner_score=owner_score,
        sell_signal_score=sell_signal_score,
        sourcing_score=sourcing_score,
        breakdown=breakdown,
        explanation=explanation,
        config_version=config.CONFIG_VERSION,
        calculated_at=datetime.now(),
    )
