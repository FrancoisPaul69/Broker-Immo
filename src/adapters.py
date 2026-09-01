"""Conversion ParcelleFiche (Pappers, réel ou démo) -> Property (domaine).

Ce module est le SEUL endroit du projet qui connaît à la fois
`pappers_types` et `schemas`. Brancher l'API réelle en Phase 3 ne touche
qu'à ce fichier et aux clients HTTP (CLAUDE.md, section 5.1).

Ce module fait une conversion STRUCTURELLE (quel champ de la réponse va où) :
il ne calcule pas encore le type_actif (voir asset_typing.qualify), ni les
champs dérivés comme prix_m2 ou l'adresse normalisée (voir data_cleaning).

TODO(données) : le schéma `Proprietaire` de l'API n'expose pas de champ
`fiabilite_appartenance_parcelle` (contrairement à `Occupant` et
`FondsDeCommerce`, section 3.5). Le lien propriété <-> propriétaire n'a donc
aujourd'hui aucune fiabilité fournie par l'API : `Ownership.fiabilite_api`
reste `None` et `confidence_score` vaut 0. Deux lectures sont possibles :
(a) rester strict et afficher "fiabilité non disponible" (retenu ici, pour
ne rien inventer) ; (b) considérer que l'inscription au cadastre fait foi et
retenir "haute" par défaut. Ce choix a un impact visible sur l'interface et
doit être tranché avec un exemple de réponse réelle ou la documentation
Pappers avant la Phase 3.
"""

from __future__ import annotations

import config
from src import pappers_types as pt
from src import schemas


def _confidence_from_fiabilite(fiabilite: str | None) -> int:
    """Mappe fiabilite_appartenance_parcelle -> confidence_score (section 3.5)."""
    if fiabilite in ("haute", "moyenne", "faible"):
        return config.FIABILITE_TO_CONFIDENCE_SCORE[fiabilite]
    if fiabilite == "":
        return config.FIABILITE_TO_CONFIDENCE_SCORE["absente"]
    return config.FIABILITE_TO_CONFIDENCE_SCORE[None]


def _bounding_box_centroid(fiche: pt.ParcelleFiche) -> tuple[float | None, float | None]:
    """Centroïde du rectangle englobant (top_left / bottom_right), quand
    demandé via champs_supplementaires=bounding_box. Coordonnée réelle,
    dérivée de données API réelles — pas une estimation inventée."""
    if fiche.top_left is None or fiche.bottom_right is None:
        return None, None
    if fiche.top_left.lat is None or fiche.bottom_right.latitude is None:
        return None, None
    if fiche.top_left.lon is None or fiche.bottom_right.longitude is None:
        return None, None
    latitude = (fiche.top_left.lat + fiche.bottom_right.latitude) / 2
    longitude = (fiche.top_left.lon + fiche.bottom_right.longitude) / 2
    return latitude, longitude


def _batiment_principal(batiments: list[pt.Batiment]) -> pt.Batiment | None:
    """Choisit le bâtiment représentatif de la parcelle : celui marqué
    parcelle_principale, sinon le premier de la liste."""
    if not batiments:
        return None
    for batiment in batiments:
        if batiment.parcelle_principale:
            return batiment
    return batiments[0]


def _convert_transaction(vente: pt.Vente, source: str) -> schemas.Transaction:
    return schemas.Transaction(
        date=vente.date,
        prix=vente.valeur_fonciere,
        surface=vente.surface_reelle_bati,
        type_mutation=vente.nature,
        type_local=vente.type_local,
        nombre_lots=vente.nombre_lots,
        prix_m2=None,  # calculé par data_cleaning.py
        prix_m2_fiable=False,  # affiné par data_cleaning.py
        source=source,
    )


def _convert_owner(proprietaire: pt.Proprietaire, source: str) -> schemas.Ownership:
    portefeuille: list[schemas.PortefeuilleApiEntry] = []
    for local in proprietaire.locaux:
        portefeuille.append(
            schemas.PortefeuilleApiEntry(
                numero_parcelle=local.numero_parcelle,
                adresse=local.adresse,
                commune=None,
                departement=local.departement,
                source=schemas.SourcePortefeuille.LOCAUX,
            )
        )
    for parcelle in proprietaire.parcelles:
        portefeuille.append(
            schemas.PortefeuilleApiEntry(
                numero_parcelle=parcelle.numero_parcelle,
                adresse=parcelle.adresse,
                commune=parcelle.nom_commune,
                departement=parcelle.departement,
                source=schemas.SourcePortefeuille.PARCELLES,
            )
        )

    owner = schemas.Owner(
        siren=proprietaire.siren,
        nom_entreprise=proprietaire.nom_entreprise,
        nom_normalise=None,  # rempli par owner_resolution.py
        type_proprietaire=schemas.TypeProprietaire.INCONNU,  # rempli par owner_resolution.py
        categorie_juridique=proprietaire.categorie_juridique,
        activite_principale=proprietaire.activite_principale,
        date_creation=proprietaire.date_creation,
        tranche_effectifs=proprietaire.tranche_effectifs,
        employeur=proprietaire.employeur,
        cessation_activite=proprietaire.cessation_activite,
        portefeuille_api=portefeuille,
        nb_parcelles_api=len(proprietaire.parcelles),
        nb_locaux_api=len(proprietaire.locaux),
        source=source,
        raw_payload=proprietaire.model_dump(mode="json"),
    )
    # Voir TODO en tête de module : pas de fiabilite_appartenance_parcelle
    # sur Proprietaire dans la spec API.
    return schemas.Ownership(
        owner=owner,
        fiabilite_api=None,
        confidence_score=_confidence_from_fiabilite(None),
        source=source,
        date_verification=None,
    )


def _convert_occupant(occupant: pt.Occupant, source: str) -> schemas.Occupant:
    return schemas.Occupant(
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
        confidence_score=_confidence_from_fiabilite(occupant.fiabilite_appartenance_parcelle),
        source=source,
        raw_payload=occupant.model_dump(mode="json"),
    )


def _convert_tiers_fonds_de_commerce(tiers: pt.TiersFondsDeCommerce | None) -> schemas.TiersFondsDeCommerce | None:
    if tiers is None:
        return None
    return schemas.TiersFondsDeCommerce(
        siren=tiers.siren,
        nom_entreprise=tiers.nom_entreprise,
        categorie_juridique=tiers.categorie_juridique,
        activite_principale=tiers.activite_principale,
        cessation_activite=tiers.cessation_activite,
    )


def _convert_fonds_de_commerce(fdc: pt.FondsDeCommerce, source: str) -> schemas.FondsDeCommerce:
    acheteur = _convert_tiers_fonds_de_commerce(fdc.acheteur)
    precedent_proprietaire = _convert_tiers_fonds_de_commerce(fdc.precedent_proprietaire)
    annonce_bodacc = None
    if fdc.annonce_bodacc is not None:
        annonce_bodacc = schemas.AnnonceBodacc(numero=fdc.annonce_bodacc.numero, date=fdc.annonce_bodacc.date)

    return schemas.FondsDeCommerce(
        activite=fdc.activite,
        prix=fdc.prix,
        date_debut_activite=fdc.date_debut_activite,
        categorie_vente=fdc.categorie_vente,
        origine_fonds=fdc.origine_fonds,
        acheteur=acheteur,
        precedent_proprietaire=precedent_proprietaire,
        annonce_bodacc=annonce_bodacc,
        fiabilite_appartenance_parcelle=fdc.fiabilite_appartenance_parcelle,
        confidence_score=_confidence_from_fiabilite(fdc.fiabilite_appartenance_parcelle),
        source=source,
        raw_payload=fdc.model_dump(mode="json"),
    )


def _convert_permis(permis: pt.Permis, source: str) -> schemas.Permis:
    return schemas.Permis(
        numero=permis.numero,
        etat=permis.etat,
        type=permis.type,
        date_autorisation=permis.date_autorisation,
        demandeur_siren=permis.demandeur.siren if permis.demandeur else None,
        source=source,
    )


def parcelle_fiche_to_property(fiche: pt.ParcelleFiche, source: str = "pappers") -> schemas.Property:
    """Convertit une ParcelleFiche (réelle ou générée par demo_source.py)
    en Property du domaine. `source` vaut "pappers" ou "demo"."""

    latitude, longitude = _bounding_box_centroid(fiche)
    batiment = _batiment_principal(fiche.batiments)
    code_postal = fiche.codes_postaux[0] if fiche.codes_postaux else None
    geometrie = fiche.geometrie.model_dump(mode="json") if fiche.geometrie else None

    return schemas.Property(
        numero_parcelle=fiche.numero or "",
        adresse_brute=fiche.adresse,
        adresse_normalisee=None,  # rempli par data_cleaning.py
        numero=None,  # rempli par data_cleaning.py
        rue=None,  # rempli par data_cleaning.py
        code_postal=code_postal,
        code_commune=fiche.code_commune,
        ville=fiche.commune,
        departement=fiche.departement,
        latitude=latitude,
        longitude=longitude,
        geometrie=geometrie,
        contenance=fiche.contenance,
        usage_batiment=batiment.usages if batiment else None,
        nature_batiment=batiment.natures if batiment else None,
        surface_batiment=batiment.surface if batiment else None,
        transactions=[_convert_transaction(v, source) for v in fiche.ventes],
        owners=[_convert_owner(p, source) for p in fiche.proprietaires],
        occupants=[_convert_occupant(o, source) for o in fiche.occupants],
        fonds_de_commerce=[_convert_fonds_de_commerce(f, source) for f in fiche.fonds_de_commerce],
        permis=[_convert_permis(p, source) for p in fiche.permis],
        source=source,
        raw_payload=fiche.model_dump(mode="json"),
    )
