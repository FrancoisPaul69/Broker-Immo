"""Script d'ingestion batch (CLAUDE.md, section 3.8).

Jamais déclenché depuis Streamlit — Streamlit ne fait que lire la base.
PostgreSQL est un cache : une parcelle déjà en base et fraîche (moins de
`config.CACHE_TTL_DAYS` jours) n'est pas réinterrogée, elle est
reconstruite depuis son `raw_payload` stocké.

Usage :

    python -m src.ingest --code-postal 69002
    python -m src.ingest --code-postal 69002 --dry-run
    DATA_SOURCE=pappers python -m src.ingest --numero-parcelle 69386AB0001 --numero-parcelle 69386AB0002

Avec DATA_SOURCE=demo (par défaut), `--code-postal` filtre le jeu DEMO
généré par `src/demo_source.py` : aucun appel réseau, aucun jeton
consommé.

Avec DATA_SOURCE=pappers, seul `--numero-parcelle` (répétable) est
supporté pour l'instant. L'ingestion par zone (`--code-postal` avec appel
réel à `GET /parcelles`) n'est pas branchée : voir le TODO dans
`src/pappers_immo_client.py` sur le schéma de réponse non documenté de
cet endpoint (règle 1, CLAUDE.md — ne pas deviner).
"""

from __future__ import annotations

import argparse
import datetime

from sqlalchemy.orm import Session

import config
from src import database
from src.demo_source import generate_demo_parcelles
from src.models import (
    FondsDeCommerceModel,
    OccupantModel,
    OwnerModel,
    OwnerPortfolioApiModel,
    OwnershipModel,
    PermisModel,
    PropertyModel,
    ScoreModel,
    TransactionModel,
)
from src.pappers_immo_client import PappersImmoClient
from src.pappers_types import ParcelleFiche
from src.pipeline import build_properties, score_properties
from src.schemas import Owner, Property, Score


def _now_utc_naive() -> datetime.datetime:
    """Horodatage naïf en UTC, comparable à `updated_at` (CURRENT_TIMESTAMP
    SQLite/Postgres, également naïf en UTC)."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _est_fraiche(model: PropertyModel | None, ttl_days: int, now: datetime.datetime) -> bool:
    if model is None or model.raw_payload is None:
        return False
    return (now - model.updated_at) < datetime.timedelta(days=ttl_days)


def _fiches_demo(code_postal: str | None) -> list[ParcelleFiche]:
    fiches = generate_demo_parcelles()
    if code_postal:
        fiches = [f for f in fiches if code_postal in (f.codes_postaux or [])]
    return fiches


def repartir_cache(
    session: Session, numeros_parcelle: list[str], ttl_days: int
) -> tuple[list[ParcelleFiche], list[str]]:
    """Sépare les numéros de parcelle demandés entre ceux déjà en base et
    frais (reconstruits depuis leur `raw_payload`, sans appel API) et ceux
    à interroger auprès de l'API."""
    now = _now_utc_naive()
    fraiches: list[ParcelleFiche] = []
    a_interroger: list[str] = []

    for numero in numeros_parcelle:
        model = session.query(PropertyModel).filter_by(numero_parcelle=numero).one_or_none()
        if _est_fraiche(model, ttl_days, now):
            fraiches.append(ParcelleFiche.model_validate(model.raw_payload))
        else:
            a_interroger.append(numero)

    return fraiches, a_interroger


def collecter_fiches(
    session: Session,
    source: str,
    code_postal: str | None,
    numeros_parcelle: list[str],
    client: PappersImmoClient | None,
    ttl_days: int,
    dry_run: bool,
) -> tuple[list[ParcelleFiche], int, int]:
    """Retourne (fiches à traiter, nombre de parcelles à interroger auprès
    de l'API, jetons documentés que cela consommerait).

    Applique le cache TTL : une parcelle déjà en base et fraîche est
    reconstruite depuis son `raw_payload` plutôt que réinterrogée. En
    dry-run, les parcelles à interroger ne sont ni appelées ni comptées
    dans les fiches retournées, seulement dans l'estimation de coût.
    """
    if source == "demo":
        return _fiches_demo(code_postal), 0, 0

    if source != "pappers":
        raise ValueError(f"DATA_SOURCE inconnu : {source!r}")

    if not numeros_parcelle:
        raise SystemExit(
            "DATA_SOURCE=pappers : l'ingestion par zone (--code-postal) n'est pas "
            "encore disponible (GET /parcelles n'a pas de schéma de réponse "
            "documenté, voir le TODO dans src/pappers_immo_client.py). "
            "Utilisez --numero-parcelle (répétable) pour cibler des parcelles précises."
        )

    assert client is not None
    fiches, a_interroger = repartir_cache(session, numeros_parcelle, ttl_days)

    if dry_run:
        cout_par_parcelle = client.estimate_cost(config.DEFAULT_CHAMPS_SUPPLEMENTAIRES)
        return fiches, len(a_interroger), cout_par_parcelle * len(a_interroger)

    for numero in a_interroger:
        fiches.append(
            client.get_parcelle_fiche(
                numero, bases=config.DEFAULT_BASES_INGESTION, champs_supplementaires=config.DEFAULT_CHAMPS_SUPPLEMENTAIRES
            )
        )

    return fiches, len(a_interroger), client.credits_used


def _proprietaires_sans_siren_deja_rattaches(model: PropertyModel) -> dict[str, OwnerModel]:
    """Propriétaires SANS SIREN déjà rattachés à CETTE parcelle (avant
    réingestion) : sert uniquement à éviter de dupliquer leur ligne
    `owners` à chaque réingestion de la même parcelle. Ne sert jamais à
    regrouper deux propriétaires sans SIREN d'une parcelle à l'autre par
    similarité de nom : sans identifiant fiable, ce serait une déduction
    non fondée (même règle que `portfolio.owners_by_siren`)."""
    return {
        ownership.owner.nom_entreprise: ownership.owner
        for ownership in model.ownerships
        if ownership.owner.siren is None and ownership.owner.nom_entreprise
    }


def _get_or_create_owner(session: Session, owner: Owner, sans_siren_connus: dict[str, OwnerModel]) -> OwnerModel:
    model = None
    if owner.siren:
        model = session.query(OwnerModel).filter_by(siren=owner.siren).one_or_none()
    elif owner.nom_entreprise:
        model = sans_siren_connus.get(owner.nom_entreprise)
    if model is None:
        model = OwnerModel(siren=owner.siren, source=owner.source)
        session.add(model)

    model.nom_entreprise = owner.nom_entreprise
    model.nom_normalise = owner.nom_normalise
    model.type_proprietaire = owner.type_proprietaire.value
    model.categorie_juridique = owner.categorie_juridique
    model.activite_principale = owner.activite_principale
    model.date_creation = owner.date_creation
    model.tranche_effectifs = owner.tranche_effectifs
    model.employeur = owner.employeur
    model.cessation_activite = owner.cessation_activite
    model.nb_parcelles_api = owner.nb_parcelles_api
    model.nb_locaux_api = owner.nb_locaux_api
    model.raw_payload = owner.raw_payload

    model.portefeuille_api.clear()
    for entree in owner.portefeuille_api:
        model.portefeuille_api.append(
            OwnerPortfolioApiModel(
                numero_parcelle=entree.numero_parcelle,
                adresse=entree.adresse,
                commune=entree.commune,
                departement=entree.departement,
                source=entree.source.value,
            )
        )
    return model


def persister_property(session: Session, property_: Property, score: Score) -> PropertyModel:
    """Insère ou met à jour un actif et ses objets liés. Les collections
    liées (transactions, occupants, fonds de commerce, permis,
    propriétaires) sont entièrement remplacées à chaque ingestion : ce
    sont des données dérivées du dernier fetch, pas des données saisies
    manuellement à préserver. Les scores, eux, s'accumulent (historique
    des calculs)."""
    model = session.query(PropertyModel).filter_by(numero_parcelle=property_.numero_parcelle).one_or_none()
    if model is None:
        model = PropertyModel(numero_parcelle=property_.numero_parcelle)
        session.add(model)

    model.adresse_brute = property_.adresse_brute
    model.adresse_normalisee = property_.adresse_normalisee
    model.numero = property_.numero
    model.rue = property_.rue
    model.code_postal = property_.code_postal
    model.code_commune = property_.code_commune
    model.ville = property_.ville
    model.departement = property_.departement
    model.latitude = property_.latitude
    model.longitude = property_.longitude
    model.geometrie = property_.geometrie
    model.contenance = property_.contenance
    model.type_actif = property_.type_actif.value
    model.type_actif_confidence = property_.type_actif_confidence.value
    model.type_actif_indices = property_.type_actif_indices
    model.usage_batiment = property_.usage_batiment
    model.nature_batiment = property_.nature_batiment
    model.surface_bati = property_.surface_bati
    model.surface_batiment = property_.surface_batiment
    model.prix_derniere_mutation = property_.prix_derniere_mutation
    model.date_derniere_mutation = property_.date_derniere_mutation
    model.nature_derniere_mutation = property_.nature_derniere_mutation
    model.type_local_vente = property_.type_local_vente
    model.nombre_lots_derniere_mutation = property_.nombre_lots_derniere_mutation
    model.prix_m2 = property_.prix_m2
    model.prix_m2_fiable = property_.prix_m2_fiable
    model.source = property_.source
    model.raw_payload = property_.raw_payload

    model.transactions.clear()
    for transaction in property_.transactions:
        model.transactions.append(
            TransactionModel(
                date=transaction.date,
                prix=transaction.prix,
                surface=transaction.surface,
                type_mutation=transaction.type_mutation,
                prix_m2=transaction.prix_m2,
                source=transaction.source,
            )
        )

    model.occupants.clear()
    for occupant in property_.occupants:
        model.occupants.append(
            OccupantModel(
                siren=occupant.siren,
                siret=occupant.siret,
                enseigne=occupant.enseigne,
                nom_entreprise=occupant.nom_entreprise,
                activite_principale_etablissement=occupant.activite_principale_etablissement,
                categorie_juridique=occupant.categorie_juridique,
                date_entree_lieux=occupant.date_entree_lieux,
                date_sortie_lieux=occupant.date_sortie_lieux,
                etablissement_ferme=occupant.etablissement_ferme,
                cessation_activite=occupant.cessation_activite,
                fiabilite_appartenance_parcelle=occupant.fiabilite_appartenance_parcelle,
                confidence_score=occupant.confidence_score,
                source=occupant.source,
                raw_payload=occupant.raw_payload,
            )
        )

    model.fonds_de_commerce.clear()
    for fdc in property_.fonds_de_commerce:
        model.fonds_de_commerce.append(
            FondsDeCommerceModel(
                activite=fdc.activite,
                prix=fdc.prix,
                date_debut_activite=fdc.date_debut_activite,
                categorie_vente=fdc.categorie_vente,
                origine_fonds=fdc.origine_fonds,
                acheteur=fdc.acheteur.model_dump(mode="json") if fdc.acheteur else None,
                precedent_proprietaire=fdc.precedent_proprietaire.model_dump(mode="json") if fdc.precedent_proprietaire else None,
                annonce_bodacc=fdc.annonce_bodacc.model_dump(mode="json") if fdc.annonce_bodacc else None,
                fiabilite_appartenance_parcelle=fdc.fiabilite_appartenance_parcelle,
                confidence_score=fdc.confidence_score,
                source=fdc.source,
                raw_payload=fdc.raw_payload,
            )
        )

    model.permis.clear()
    for permis in property_.permis:
        model.permis.append(
            PermisModel(
                numero=permis.numero,
                etat=permis.etat,
                type=permis.type,
                date_autorisation=permis.date_autorisation,
                demandeur_siren=permis.demandeur_siren,
                source=permis.source,
            )
        )

    sans_siren_connus = _proprietaires_sans_siren_deja_rattaches(model)
    model.ownerships.clear()
    for ownership in property_.owners:
        owner_model = _get_or_create_owner(session, ownership.owner, sans_siren_connus)
        model.ownerships.append(
            OwnershipModel(
                owner=owner_model,
                confidence_score=ownership.confidence_score,
                fiabilite_api=ownership.fiabilite_api,
                source=ownership.source,
                date_verification=ownership.date_verification,
            )
        )

    model.scores.append(
        ScoreModel(
            asset_score=score.asset_score,
            owner_score=score.owner_score,
            sell_signal_score=score.sell_signal_score,
            sourcing_score=score.sourcing_score,
            score_breakdown=[item.model_dump(mode="json") for item in score.breakdown],
            score_explanation=score.explanation,
            config_version=score.config_version,
            calculated_at=score.calculated_at,
        )
    )

    return model


def run(
    session: Session,
    source: str,
    code_postal: str | None = None,
    numeros_parcelle: list[str] | None = None,
    client: PappersImmoClient | None = None,
    ttl_days: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Orchestration complète : collecte -> pipeline -> persistance.

    Retourne un résumé (nombre d'actifs traités, jetons consommés) affiché
    par le CLI et réutilisable en test.
    """
    ttl_days = ttl_days if ttl_days is not None else config.CACHE_TTL_DAYS
    numeros_parcelle = numeros_parcelle or []

    fiches, nb_a_interroger, jetons = collecter_fiches(session, source, code_postal, numeros_parcelle, client, ttl_days, dry_run)

    resume = {
        "source": source,
        "nb_fiches": len(fiches),
        "nb_parcelles_a_interroger": nb_a_interroger,
        "jetons": jetons,
        "dry_run": dry_run,
    }
    if dry_run:
        return resume

    properties = build_properties(fiches, source=source)
    scores = score_properties(properties)
    for property_ in properties:
        persister_property(session, property_, scores[property_.numero_parcelle])
    session.commit()

    return resume


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--code-postal", default=None, help="Filtre par code postal (mode demo uniquement pour l'instant).")
    parser.add_argument(
        "--numero-parcelle",
        action="append",
        default=[],
        help="Numéro de parcelle à ingérer (répétable). Requis en DATA_SOURCE=pappers.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Estime le coût en jetons sans appeler l'API ni écrire en base.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    engine = database.get_engine()
    session_factory = database.get_session_factory(engine)
    client = PappersImmoClient() if config.DATA_SOURCE == "pappers" else None

    with database.session_scope(session_factory) as session:
        resume = run(
            session,
            source=config.DATA_SOURCE,
            code_postal=args.code_postal,
            numeros_parcelle=args.numero_parcelle,
            client=client,
            dry_run=args.dry_run,
        )

    verbe = "estimés" if resume["dry_run"] else "consommés"
    print(f"Source : {resume['source']}")
    print(f"Actifs {'concernés' if resume['dry_run'] else 'traités'} : {resume['nb_fiches']}")
    print(f"Parcelles à interroger auprès de l'API : {resume['nb_parcelles_a_interroger']}")
    print(f"Jetons {verbe} (surcoûts documentés uniquement) : {resume['jetons']}")
    if resume["source"] == "pappers":
        print(
            "Attention : ce total sous-estime la consommation réelle, le coût de base "
            "d'une requête n'étant pas documenté (voir config.py)."
        )
    if resume["dry_run"]:
        print("Dry-run : aucun appel API, aucune écriture en base.")


if __name__ == "__main__":
    main()
