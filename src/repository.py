"""Reconstruction du modèle de domaine (schemas.py) depuis les lignes
persistées par `src/ingest.py` — le mapping inverse de
`ingest.persister_property`.

Seule porte d'entrée que `ui/` doit utiliser pour lire des données
(CLAUDE.md, section 5 : Streamlit ne lit que la base, aucun appel à
`demo_source`/`pipeline` depuis `ui/`).

Le score retourné pour chaque actif est le PLUS RÉCENT
(`calculated_at` le plus grand) : `scores` accumule un historique, voir
`ingest.persister_property`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.models import OwnerModel, OwnershipModel, PropertyModel, ScoreModel
from src.schemas import (
    AnnonceBodacc,
    ConfianceTyping,
    FondsDeCommerce,
    Occupant,
    Owner,
    Ownership,
    Permis,
    PortefeuilleApiEntry,
    Property,
    Score,
    ScoreBreakdownItem,
    SourcePortefeuille,
    TiersFondsDeCommerce,
    Transaction,
    TypeActif,
    TypeProprietaire,
)


def _tiers_fonds_de_commerce(payload: dict | None) -> TiersFondsDeCommerce | None:
    return TiersFondsDeCommerce.model_validate(payload) if payload else None


def _annonce_bodacc(payload: dict | None) -> AnnonceBodacc | None:
    return AnnonceBodacc.model_validate(payload) if payload else None


def _owner_domain(model) -> Owner:
    return Owner(
        siren=model.siren,
        nom_entreprise=model.nom_entreprise,
        nom_normalise=model.nom_normalise,
        type_proprietaire=TypeProprietaire(model.type_proprietaire),
        categorie_juridique=model.categorie_juridique,
        activite_principale=model.activite_principale,
        date_creation=model.date_creation,
        tranche_effectifs=model.tranche_effectifs,
        employeur=model.employeur,
        cessation_activite=model.cessation_activite,
        portefeuille_api=[
            PortefeuilleApiEntry(
                numero_parcelle=entry.numero_parcelle,
                adresse=entry.adresse,
                commune=entry.commune,
                departement=entry.departement,
                source=SourcePortefeuille(entry.source),
            )
            for entry in model.portefeuille_api
        ],
        nb_parcelles_api=model.nb_parcelles_api,
        nb_locaux_api=model.nb_locaux_api,
        source=model.source,
        raw_payload=model.raw_payload,
    )


def _score_domain(model: ScoreModel, numero_parcelle: str) -> Score:
    return Score(
        numero_parcelle=numero_parcelle,
        asset_score=model.asset_score,
        owner_score=model.owner_score,
        sell_signal_score=model.sell_signal_score,
        sourcing_score=model.sourcing_score,
        breakdown=[ScoreBreakdownItem.model_validate(item) for item in (model.score_breakdown or [])],
        explanation=model.score_explanation or "",
        config_version=model.config_version,
        calculated_at=model.calculated_at,
    )


def _property_domain(model: PropertyModel) -> Property:
    return Property(
        numero_parcelle=model.numero_parcelle,
        adresse_brute=model.adresse_brute,
        adresse_normalisee=model.adresse_normalisee,
        numero=model.numero,
        rue=model.rue,
        code_postal=model.code_postal,
        code_commune=model.code_commune,
        ville=model.ville,
        departement=model.departement,
        latitude=model.latitude,
        longitude=model.longitude,
        geometrie=model.geometrie,
        contenance=model.contenance,
        type_actif=TypeActif(model.type_actif) if model.type_actif else TypeActif.INCERTAIN,
        type_actif_confidence=ConfianceTyping(model.type_actif_confidence) if model.type_actif_confidence else ConfianceTyping.FAIBLE,
        type_actif_indices=model.type_actif_indices or [],
        usage_batiment=model.usage_batiment,
        nature_batiment=model.nature_batiment,
        surface_bati=model.surface_bati,
        surface_batiment=model.surface_batiment,
        prix_derniere_mutation=model.prix_derniere_mutation,
        date_derniere_mutation=model.date_derniere_mutation,
        nature_derniere_mutation=model.nature_derniere_mutation,
        type_local_vente=model.type_local_vente,
        nombre_lots_derniere_mutation=model.nombre_lots_derniere_mutation,
        prix_m2=model.prix_m2,
        prix_m2_fiable=model.prix_m2_fiable,
        transactions=[
            Transaction(
                date=t.date,
                prix=t.prix,
                surface=t.surface,
                type_mutation=t.type_mutation,
                prix_m2=t.prix_m2,
                source=t.source,
            )
            for t in model.transactions
        ],
        owners=[
            Ownership(
                owner=_owner_domain(ownership.owner),
                fiabilite_api=ownership.fiabilite_api,
                confidence_score=ownership.confidence_score,
                source=ownership.source,
                date_verification=ownership.date_verification,
            )
            for ownership in model.ownerships
        ],
        occupants=[
            Occupant(
                siren=o.siren,
                siret=o.siret,
                enseigne=o.enseigne,
                nom_entreprise=o.nom_entreprise,
                activite_principale_etablissement=o.activite_principale_etablissement,
                categorie_juridique=o.categorie_juridique,
                date_entree_lieux=o.date_entree_lieux,
                date_sortie_lieux=o.date_sortie_lieux,
                etablissement_ferme=o.etablissement_ferme,
                cessation_activite=o.cessation_activite,
                fiabilite_appartenance_parcelle=o.fiabilite_appartenance_parcelle,
                confidence_score=o.confidence_score,
                source=o.source,
                raw_payload=o.raw_payload,
            )
            for o in model.occupants
        ],
        fonds_de_commerce=[
            FondsDeCommerce(
                activite=f.activite,
                prix=f.prix,
                date_debut_activite=f.date_debut_activite,
                categorie_vente=f.categorie_vente,
                origine_fonds=f.origine_fonds,
                acheteur=_tiers_fonds_de_commerce(f.acheteur),
                precedent_proprietaire=_tiers_fonds_de_commerce(f.precedent_proprietaire),
                annonce_bodacc=_annonce_bodacc(f.annonce_bodacc),
                fiabilite_appartenance_parcelle=f.fiabilite_appartenance_parcelle,
                confidence_score=f.confidence_score,
                source=f.source,
                raw_payload=f.raw_payload,
            )
            for f in model.fonds_de_commerce
        ],
        permis=[
            Permis(
                numero=p.numero,
                etat=p.etat,
                type=p.type,
                date_autorisation=p.date_autorisation,
                demandeur_siren=p.demandeur_siren,
                source=p.source,
            )
            for p in model.permis
        ],
        source=model.source,
        raw_payload=model.raw_payload,
    )


def load_properties(session: Session, code_postal: str | None = None) -> tuple[list[Property], dict[str, Score]]:
    """Charge tous les actifs (et leur dernier score calculé) depuis la
    base, avec chargement anticipé des relations pour éviter le
    N+1 (`selectinload`). Retourne la même forme que
    `src.pipeline.build_properties` / `score_properties`, pour que `ui/`
    n'ait pas à distinguer sa source."""
    stmt = (
        select(PropertyModel)
        .options(
            selectinload(PropertyModel.transactions),
            selectinload(PropertyModel.occupants),
            selectinload(PropertyModel.fonds_de_commerce),
            selectinload(PropertyModel.permis),
            selectinload(PropertyModel.ownerships).selectinload(OwnershipModel.owner).selectinload(OwnerModel.portefeuille_api),
            selectinload(PropertyModel.scores),
        )
        .order_by(PropertyModel.numero_parcelle)
    )
    if code_postal:
        stmt = stmt.where(PropertyModel.code_postal == code_postal)

    models = session.execute(stmt).unique().scalars().all()

    properties: list[Property] = []
    scores: dict[str, Score] = {}
    for model in models:
        properties.append(_property_domain(model))
        if model.scores:
            dernier = max(model.scores, key=lambda s: s.calculated_at)
            scores[model.numero_parcelle] = _score_domain(dernier, model.numero_parcelle)

    return properties, scores
