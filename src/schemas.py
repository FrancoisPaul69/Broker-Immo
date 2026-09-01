"""Modèles Pydantic du domaine — couche pivot (CLAUDE.md, section 5.1).

Ces classes décrivent NOTRE modèle métier de sourcing immobilier, pas celui
de Pappers. `adapters.py` convertit les payloads `pappers_types.ParcelleFiche`
(réels ou générés par `demo_source.py`) en objets `Property` définis ici.

Tout le reste du code (cleaning, resolution, scoring, explications, UI) ne
doit connaître que ces classes — jamais `pappers_types`. C'est ce qui permet
de brancher l'API réelle en Phase 3 sans toucher au reste du pipeline.

Une donnée absente est `None`, jamais devinée (règle 2, CLAUDE.md).
"""

from __future__ import annotations

import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

# date/datetime référencés via `datetime.date` / `datetime.datetime` (jamais
# importés nommément) : Transaction.date et AnnonceBodacc.date s'appellent
# littéralement "date", ce qui rendrait `date: datetime.date | None` ambigu pour la
# résolution différée des annotations par Pydantic (même contrainte que
# pappers_types.py).


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TypeActif(str, Enum):
    """Résultat de la qualification par faisceau d'indices (src/asset_typing.py)."""

    COMMERCIAL = "commercial"
    INDUSTRIEL_OU_ENTREPOT = "industriel_ou_entrepot"
    AUTRE = "autre"  # appartement, maison, dependance : hors périmètre commercial
    INCERTAIN = "incertain"


class ConfianceTyping(str, Enum):
    HAUTE = "haute"
    MOYENNE = "moyenne"
    FAIBLE = "faible"


class TypeProprietaire(str, Enum):
    PERSONNE_PHYSIQUE = "personne_physique"
    SCI = "sci"
    FONCIERE = "fonciere"
    INSTITUTIONNEL = "institutionnel"
    SOCIETE = "societe"
    EXPLOITANT = "exploitant"
    AUTRE = "autre"
    INCONNU = "inconnu"


class SourcePortefeuille(str, Enum):
    LOCAUX = "locaux"
    PARCELLES = "parcelles"


class Transaction(DomainModel):
    """Une mutation (vente) sur la parcelle. Correspond à la table `transactions`."""

    date: datetime.date | None = None
    prix: float | None = None  # jamais "valeur" (section 3.6)
    surface: float | None = None
    type_mutation: str | None = None  # Vente.nature : vente/echange/adjudication...
    type_local: str | None = None  # Vente.type_local (DVF)
    nombre_lots: int | None = None
    prix_m2: float | None = None
    prix_m2_fiable: bool = False  # False si mutation multi-lots (section 3.6)
    source: str = "pappers"


class PortefeuilleApiEntry(DomainModel):
    """Une ligne du portefeuille déclaré par l'API pour un propriétaire
    (table `owner_portfolio_api`). Ne JAMAIS fusionner avec les actifs
    réellement ingérés dans `properties` (section 3.4)."""

    numero_parcelle: str | None = None
    adresse: str | None = None
    commune: str | None = None
    departement: str | None = None
    source: SourcePortefeuille


class Owner(DomainModel):
    """Correspond à la table `owners`."""

    siren: str | None = None
    nom_entreprise: str | None = None
    nom_normalise: str | None = None
    type_proprietaire: TypeProprietaire = TypeProprietaire.INCONNU
    categorie_juridique: str | None = None
    activite_principale: str | None = None
    date_creation: datetime.date | None = None
    tranche_effectifs: str | None = None
    employeur: bool | None = None
    cessation_activite: bool | None = None
    portefeuille_api: list[PortefeuilleApiEntry] = []
    nb_parcelles_api: int = 0
    nb_locaux_api: int = 0
    source: str = "pappers"
    raw_payload: dict | None = None


class Ownership(DomainModel):
    """Lien propriété <-> propriétaire, avec sa fiabilité (table `ownership`).

    fiabilite_api conserve la valeur brute (haute/moyenne/faible/None),
    confidence_score est sa normalisation via
    config.FIABILITE_TO_CONFIDENCE_SCORE (section 3.5).
    """

    owner: Owner
    fiabilite_api: str | None = None
    confidence_score: int = 0
    source: str = "pappers"
    date_verification: datetime.date | None = None


class TiersFondsDeCommerce(DomainModel):
    siren: str | None = None
    nom_entreprise: str | None = None
    categorie_juridique: str | None = None
    activite_principale: str | None = None
    cessation_activite: bool | None = None


class AnnonceBodacc(DomainModel):
    numero: int | None = None
    date: datetime.date | None = None


class FondsDeCommerce(DomainModel):
    """Correspond à la table `fonds_de_commerce`."""

    activite: str | None = None
    prix: float | None = None
    date_debut_activite: datetime.date | None = None
    categorie_vente: str | None = None
    origine_fonds: str | None = None
    acheteur: TiersFondsDeCommerce | None = None
    precedent_proprietaire: TiersFondsDeCommerce | None = None
    annonce_bodacc: AnnonceBodacc | None = None
    fiabilite_appartenance_parcelle: str | None = None
    confidence_score: int = 0
    source: str = "pappers"
    raw_payload: dict | None = None


class Occupant(DomainModel):
    """Correspond à la table `occupants`."""

    siren: str | None = None
    siret: str | None = None
    enseigne: str | None = None
    nom_entreprise: str | None = None
    activite_principale_etablissement: str | None = None
    categorie_juridique: str | None = None
    date_entree_lieux: datetime.date | None = None
    date_sortie_lieux: datetime.date | None = None
    etablissement_ferme: bool | None = None
    cessation_activite: bool | None = None
    fiabilite_appartenance_parcelle: str | None = None
    confidence_score: int = 0
    source: str = "pappers"
    raw_payload: dict | None = None


class Permis(DomainModel):
    numero: str | None = None
    etat: str | None = None
    type: str | None = None
    date_autorisation: datetime.date | None = None
    demandeur_siren: str | None = None
    source: str = "pappers"


class Property(DomainModel):
    """Un actif (local) — correspond à la table `properties`, enrichie des
    objets liés (transactions, propriétaires, occupants, fonds de
    commerce, permis) tels que produits par adapters.py."""

    numero_parcelle: str
    adresse_brute: str | None = None
    adresse_normalisee: str | None = None
    numero: str | None = None
    rue: str | None = None
    code_postal: str | None = None
    code_commune: str | None = None
    ville: str | None = None
    departement: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geometrie: dict | None = None
    contenance: float | None = None

    type_actif: TypeActif = TypeActif.INCERTAIN
    type_actif_confidence: ConfianceTyping = ConfianceTyping.FAIBLE
    type_actif_indices: list[str] = []

    usage_batiment: str | None = None
    nature_batiment: str | None = None
    surface_bati: float | None = None
    surface_batiment: float | None = None

    prix_derniere_mutation: float | None = None
    date_derniere_mutation: datetime.date | None = None
    nature_derniere_mutation: str | None = None  # Vente.nature : vente/echange/adjudication...
    type_local_vente: str | None = None  # Vente.type_local (DVF) : entrée n°1 de asset_typing
    nombre_lots_derniere_mutation: int | None = None
    prix_m2: float | None = None
    prix_m2_fiable: bool = False

    transactions: list[Transaction] = []
    owners: list[Ownership] = []
    occupants: list[Occupant] = []
    fonds_de_commerce: list[FondsDeCommerce] = []
    permis: list[Permis] = []

    source: str = "pappers"  # "demo" ou "pappers"
    raw_payload: dict | None = None


class ScoreBreakdownItem(DomainModel):
    """Une ligne du détail de score, affichée dans la fiche actif
    ("Pourquoi cet actif ?")."""

    critere: str
    points: float
    points_max: float
    detail: str


class Score(DomainModel):
    """Correspond à la table `scores`."""

    numero_parcelle: str
    asset_score: float
    owner_score: float
    sell_signal_score: float
    sourcing_score: float
    breakdown: list[ScoreBreakdownItem]
    explanation: str
    config_version: str
    calculated_at: datetime.datetime
