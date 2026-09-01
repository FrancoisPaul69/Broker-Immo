"""Mapping fidèle des schémas de l'API Pappers Immobilier (spec OpenAPI 1.0.0).

Ces modèles décrivent EXACTEMENT ce que l'API peut renvoyer (voir
docs/api_1_0_0.yaml). Ils ne doivent contenir aucun champ inventé (règle 1,
CLAUDE.md). Rien d'autre dans le projet ne doit dépendre de ces classes
directement : la conversion vers le modèle de domaine se fait dans
adapters.py (voir CLAUDE.md, section 5.1).

Le schéma Dpe compte une centaine de champs techniques (isolation,
ventilation, vitrages...) qui n'entrent dans aucun critère de qualification
ou de scoring en V1 (ni asset_typing.py, ni scoring.py, ni le modèle de
données de la section 6). Plutôt que de recopier l'intégralité du schéma
sans usage, seuls les champs utiles sont déclarés et `extra="allow"`
laisse passer le reste tel quel : aucune information n'est perdue
(le payload brut est de toute façon conservé en JSONB), mais le code
reste lisible. Les autres schémas sont mappés champ par champ.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict

# Le type date est référencé comme `datetime.date` (jamais `date` importé
# nommément) : plusieurs champs de la spec s'appellent littéralement "date"
# (Vente.date, AnnonceBodacc.date), et `date: date | None` rendrait le nom
# `date` ambigu pour la résolution différée des annotations par Pydantic.


class PappersBaseModel(BaseModel):
    """Base commune : ignore silencieusement les champs non documentés
    plutôt que de lever une erreur (l'API peut ajouter des champs)."""

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# ParcelleBase
# ---------------------------------------------------------------------------
class AutreAdresse(PappersBaseModel):
    adresse: str | None = None
    sources: list[str] | None = None


class LatLon(PappersBaseModel):
    lat: float | None = None
    lon: float | None = None


class BottomRight(PappersBaseModel):
    latitude: float | None = None
    longitude: float | None = None


class Geometrie(PappersBaseModel):
    type: str | None = None
    coordinates: list | None = None


class ParcelleBase(PappersBaseModel):
    numero: str | None = None
    section: str | None = None
    prefixe: str | None = None
    numero_plan: str | None = None
    adresse: str | None = None
    sources_adresse: list[str] | None = None
    autres_adresses: list[AutreAdresse] | None = None
    code_commune: str | None = None
    commune: str | None = None
    code_region: str | None = None
    region: str | None = None
    code_departement: str | None = None
    departement: str | None = None
    codes_postaux: list[str] | None = None
    contenance: float | None = None
    arpente: bool | None = None
    top_left: LatLon | None = None
    bottom_right: BottomRight | None = None
    geometrie: Geometrie | None = None


# ---------------------------------------------------------------------------
# Vente
# ---------------------------------------------------------------------------
class VenteLot(PappersBaseModel):
    numero: str | None = None
    surface_carrez: float | None = None


class Vente(PappersBaseModel):
    id: str | None = None
    date: datetime.date | None = None
    nature: str | None = None  # enum nature_vente
    valeur_fonciere: float | None = None
    code_type_local: str | None = None
    type_local: str | None = None  # enum type_local_vente
    surface_reelle_bati: float | None = None
    surface_terrain: float | None = None
    nombre_pieces: int | None = None
    code_nature_culture: str | None = None
    nature_culture: str | None = None
    code_nature_culture_speciale: str | None = None
    nature_culture_speciale: str | None = None
    ancienne_parcelle_cadastrale: str | None = None
    nombre_lots: int | None = None
    lots: list[VenteLot] | None = None
    adresse: str | None = None


# ---------------------------------------------------------------------------
# Copropriete
# ---------------------------------------------------------------------------
class SyndicProfessionnel(PappersBaseModel):
    siret: str | None = None
    nom_entreprise: str | None = None


class RepresentantLegalCopropriete(PappersBaseModel):
    siret: str | None = None
    nom_entreprise: str | None = None


class QuartierPrioritaire(PappersBaseModel):
    nom_2024: str | None = None
    code_2024: str | None = None
    nom_2015: str | None = None
    code_2015: str | None = None


class AppartenancesCopropriete(PappersBaseModel):
    action_coeur_de_ville: bool | None = None
    petites_villes_de_demain: bool | None = None
    copropriete_aidee: bool | None = None
    quartier_prioritaire: QuartierPrioritaire | None = None


class RattachementsSyndicat(PappersBaseModel):
    nombre_asl: int | None = None
    nombre_aful: int | None = None
    nombre_unions_syndicats: int | None = None


class Copropriete(PappersBaseModel):
    nom: str | None = None
    numero_immatriculation: str | None = None
    numero_immatriculation_principal: str | None = None
    mandat_en_cours: str | None = None
    nombre_total_lots: int | None = None
    nombre_total_lots_a_usage_habitation_bureaux_commerces: int | None = None
    nombre_lots_a_usage_habitation: int | None = None
    nombre_lots_stationnement: int | None = None
    periode_construction: str | None = None
    type_syndic: str | None = None  # enum type_syndic_copropriete
    syndic_professionnel: SyndicProfessionnel | None = None
    syndicat_cooperatif: bool | None = None
    syndicat_principal_ou_syndicat_secondaire: str | None = None
    representant_legal: RepresentantLegalCopropriete | None = None
    date_immatriculation: datetime.date | None = None
    date_reglement_copropriete: datetime.date | None = None
    residence_service: bool | None = None
    appartenances: AppartenancesCopropriete | None = None
    rattachements_syndicat: RattachementsSyndicat | None = None
    autres_parcelles: list[str] | None = None
    nombre_parcelles_cadastrales: int | None = None
    date_mise_a_jour_rnic: datetime.date | None = None
    date_derniere_maj: datetime.date | None = None
    date_fin_dernier_mandat: datetime.date | None = None
    adresse: str | None = None


# ---------------------------------------------------------------------------
# Batiment
# ---------------------------------------------------------------------------
class Batiment(PappersBaseModel):
    parcelle_principale: bool | None = None
    batiment_groupe_id: str | None = None
    code_epci: str | None = None
    surface: float | None = None
    code_iris: str | None = None
    natures: str | None = None  # enum nature_batiment (libellés longs)
    usages: str | None = None  # enum usage_batiment (libellés longs)
    etat: str | None = None
    hauteur_moyenne: float | None = None
    hauteur_max: float | None = None
    altitude_moyenne_du_sol: float | None = None
    zone_activite_nature: str | None = None
    zone_activite_nature_detaillee: str | None = None
    zone_activite_toponyme: str | None = None
    annee_construction: int | None = None
    materiaux_mur: str | None = None
    materiaux_toit: str | None = None
    nombre_logements: int | None = None


# ---------------------------------------------------------------------------
# Dpe (sous-ensemble utile ; voir docstring de module)
# ---------------------------------------------------------------------------
class Dpe(BaseModel):
    model_config = ConfigDict(extra="allow")

    identifiant_dpe: str | None = None
    date_etablissement_dpe: datetime.date | None = None
    classe_bilan_dpe: str | None = None  # enum A-G
    classe_emission_ges: str | None = None  # enum A-G
    type_installation_chauffage: str | None = None
    type_energie_chauffage: str | None = None
    surface_habitable_logement: float | None = None
    parcelle_cadastrale: str | None = None


# ---------------------------------------------------------------------------
# Proprietaire
# ---------------------------------------------------------------------------
class ProprietaireLocal(PappersBaseModel):
    numero_parcelle: str | None = None
    code_droit: str | None = None
    batiment: str | None = None
    entree: str | None = None
    niveau: str | None = None
    porte: str | None = None
    numero_voie: str | None = None
    nature_voie: str | None = None
    nom_voie: str | None = None
    departement: str | None = None
    adresse: str | None = None


class ProprietaireParcelle(PappersBaseModel):
    numero_parcelle: str | None = None
    departement: str | None = None
    code_direction: str | None = None
    code_commune: str | None = None
    nom_commune: str | None = None
    indice_repetition: str | None = None
    code_voie_majic: str | None = None
    code_voie_rivoli: str | None = None
    nature_voie: str | None = None
    nom_voie: str | None = None
    numero_voie: str | None = None
    contenance: float | None = None
    suf: str | None = None
    nature_culture: str | None = None
    contenance_suf: float | None = None
    code_droit: str | None = None
    numero_majic: str | None = None
    groupe_personne: str | None = None
    adresse: str | None = None


class PersonnePhysique(PappersBaseModel):
    nom_patronymique: str | None = None
    nom_usage: str | None = None
    prenoms: str | None = None
    nom_complet: str | None = None
    nationalite: str | None = None
    beneficiaire_representant_legal: bool | None = None
    detention_part_totale: str | None = None
    detention_part_directe: bool | None = None
    detention_part_indirecte: bool | None = None
    detention_vote_directe: bool | None = None
    detention_vote_indirecte: bool | None = None
    detention_vote_total: str | None = None
    date_de_naissance: str | None = None  # format AAAA-MM, pas une date complète
    date_de_naissance_formatee: str | None = None
    identifier: str | None = None
    qualite: str | None = None
    qualites: list[str] | None = None
    dirigeant: bool | None = None
    beneficiaire: bool | None = None


class RepresentantPersonneMorale(PappersBaseModel):
    siren: str | None = None
    denomination: str | None = None
    nom_entreprise: str | None = None
    sigle_denomination_completion: str | None = None
    qualite: str | None = None
    qualites: list[str] | None = None
    forme_juridique: str | None = None
    forme_juridique_code: str | None = None


class Proprietaire(PappersBaseModel):
    siren: str | None = None
    date_creation: datetime.date | None = None
    nom_entreprise: str | None = None
    tranche_effectifs: str | None = None
    annee_effectifs: str | None = None
    categorie_juridique: str | None = None
    activite_principale: str | None = None
    employeur: bool | None = None
    cessation_activite: bool | None = None
    locaux: list[ProprietaireLocal] = []
    parcelles: list[ProprietaireParcelle] = []
    personnes_physiques: list[PersonnePhysique] = []
    representants_personnes_morales: list[RepresentantPersonneMorale] = []


# ---------------------------------------------------------------------------
# Occupant
# ---------------------------------------------------------------------------
class Occupant(PappersBaseModel):
    siren: str | None = None
    siret: str | None = None
    fiabilite_appartenance_parcelle: str | None = None  # enum faible/moyenne/haute
    date_entree_lieux: datetime.date | None = None
    tranche_effectifs_etablissement: str | None = None
    annee_effectifs_etablissement: int | None = None
    activite_principale_etablissement: str | None = None
    nomenclature_activite_principale_etablissement: str | None = None
    categorie_juridique: str | None = None
    enseigne: str | None = None
    cessation_activite: bool | None = None
    etablissement_ferme: bool | None = None
    date_sortie_lieux: datetime.date | None = None
    nom_entreprise: str | None = None
    adresse: str | None = None


# ---------------------------------------------------------------------------
# FondsDeCommerce
# ---------------------------------------------------------------------------
class AnnonceBodacc(PappersBaseModel):
    numero_parution: int | None = None
    numero: int | None = None
    date: datetime.date | None = None


class TiersFondsDeCommerce(PappersBaseModel):
    """Structure commune à acheteur / precedent_proprietaire / precedent_exploitant."""

    siren: str | None = None
    nom_entreprise: str | None = None
    categorie_juridique: str | None = None
    activite_principale: str | None = None
    nomenclature_activite_principale: str | None = None
    cessation_activite: bool | None = None


class FondsDeCommerce(PappersBaseModel):
    activite: str | None = None
    prix: float | None = None
    devise: str | None = None
    categorie_vente: str | None = None
    origine_fonds: str | None = None
    commentaires: str | None = None
    date_debut_activite: datetime.date | None = None
    annonce_bodacc: AnnonceBodacc | None = None
    acheteur: TiersFondsDeCommerce | None = None
    precedent_proprietaire: TiersFondsDeCommerce | None = None
    precedent_exploitant: TiersFondsDeCommerce | None = None
    fiabilite_appartenance_parcelle: str | None = None  # enum faible/moyenne/haute
    adresse: str | None = None


# ---------------------------------------------------------------------------
# Permis
# ---------------------------------------------------------------------------
class DemandeurPermis(PappersBaseModel):
    siren: str | None = None
    siret: str | None = None
    code_naf: str | None = None
    categorie_juridique: str | None = None
    code_postal: str | None = None
    denomination: str | None = None
    commune: str | None = None


class Permis(PappersBaseModel):
    numero: str | None = None
    etat: str | None = None  # enum statut_permis
    type: str | None = None
    date_autorisation: datetime.date | None = None
    annee_depot: str | None = None
    demandeur: DemandeurPermis | None = None
    recours_architecte: bool | None = None
    autres_parcelles: list[str] | None = None
    superficie_terrain: float | None = None
    zone_operatoire: str | None = None
    adresse: str | None = None


# ---------------------------------------------------------------------------
# ParcelleFiche = ParcelleBase + un tableau par base demandée
# ---------------------------------------------------------------------------
class ParcelleFiche(ParcelleBase):
    ventes: list[Vente] = []
    batiments: list[Batiment] = []
    dpe: list[Dpe] = []
    fonds_de_commerce: list[FondsDeCommerce] = []
    occupants: list[Occupant] = []
    proprietaires: list[Proprietaire] = []
    coproprietes: list[Copropriete] = []
    permis: list[Permis] = []


# ---------------------------------------------------------------------------
# ParcelleSearchParams — les 76 paramètres de GET /parcelles (CLAUDE.md,
# section 3.2). Un seul modèle Pydantic pour la pagination/curseur, les
# bases demandées et l'ensemble des filtres de recherche.
# ---------------------------------------------------------------------------
class ParcelleSearchParams(PappersBaseModel):
    # Pagination et bases (section 3.8 : `page` plafonné à 400 résultats,
    # utiliser `curseur` pour un balayage complet de zone).
    par_page: int | None = None
    page: int | None = None
    curseur: str | None = None
    bases: list[str] | None = None  # proprietaires, ventes, batiments, dpe, occupants, permis, fonds_de_commerce, coproprietes
    champs_supplementaires: list[str] | None = None  # jamais "tous" (règle 3.8), voir config.CHAMPS_SUPPLEMENTAIRES_COUTS

    # Zone
    parcelle_cadastrale: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    code_commune: str | None = None
    region: str | None = None
    departement: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance: int | None = None

    # Copropriété
    type_syndic_copropriete: str | None = None  # enum: professionnel, benevole
    siret_syndic_professionnel_copropriete: str | None = None
    nom_copropriete: str | None = None
    nombre_lots_copropriete_min: int | None = None
    nombre_lots_copropriete_max: int | None = None
    nombre_coproprietes_min: int | None = None
    nombre_coproprietes_max: int | None = None

    # Propriétaire
    siren_proprietaire: str | None = None
    tranche_effectif_proprietaire_min: str | None = None
    tranche_effectif_proprietaire_max: str | None = None
    categorie_juridique_proprietaire: str | None = None
    code_naf_proprietaire: str | None = None
    denomination_proprietaire: str | None = None
    nombre_proprietaires_min: int | None = None
    nombre_proprietaires_max: int | None = None

    # Occupant
    siren_occupant: str | None = None
    tranche_effectif_occupant_min: str | None = None
    tranche_effectif_occupant_max: str | None = None
    categorie_juridique_occupant: str | None = None
    code_naf_occupant: str | None = None
    denomination_occupant: str | None = None
    nombre_occupants_min: int | None = None
    nombre_occupants_max: int | None = None

    # Actif / ventes (DVF)
    nature_vente: str | None = None  # enum: vente, echange, adjudication, expropriation, vente_futur_achevement, vente_terrain_batir
    type_local_vente: str | None = None  # enum: appartement, maison, dependance, local_industriel_commercial_ou_assimile
    date_vente_min: datetime.date | None = None
    date_vente_max: datetime.date | None = None
    prix_vente_min: int | None = None
    prix_vente_max: int | None = None
    surface_bati_vente_min: int | None = None
    surface_bati_vente_max: int | None = None
    surface_terrain_vente_min: int | None = None
    surface_terrain_vente_max: int | None = None
    nombre_pieces_vente_min: int | None = None
    nombre_pieces_vente_max: int | None = None
    nombre_ventes_min: int | None = None
    nombre_ventes_max: int | None = None

    # Bâtiment
    annee_construction_batiment_min: int | None = None
    annee_construction_batiment_max: int | None = None
    nombre_logements_batiment_min: int | None = None
    nombre_logements_batiment_max: int | None = None
    surface_batiment_min: int | None = None
    surface_batiment_max: int | None = None
    nature_batiment: str | None = None
    usage_batiment: str | None = None
    nombre_batiments_min: int | None = None
    nombre_batiments_max: int | None = None

    # DPE
    classe_bilan_dpe: str | None = None  # enum: A, B, C, D, E, F, G
    type_installation_chauffage_dpe: str | None = None  # enum: individuel, collectif
    type_energie_chauffage_dpe: str | None = None  # enum: gaz, electricite, fioul, bois, gpl_butane_propane, solaire, charbon, reseau_de_chaleur

    # Fonds de commerce
    prix_fonds_de_commerce_min: int | None = None
    prix_fonds_de_commerce_max: int | None = None
    date_fonds_de_commerce_min: datetime.date | None = None
    date_fonds_de_commerce_max: datetime.date | None = None
    code_naf_fonds_de_commerce: str | None = None
    nombre_fonds_de_commerce_min: int | None = None
    nombre_fonds_de_commerce_max: int | None = None

    # Permis
    statut_permis: str | None = None  # enum: autorise, commence, termine, annule
    date_autorisation_permis_min: datetime.date | None = None
    date_autorisation_permis_max: datetime.date | None = None
    nombre_permis_min: int | None = None
    nombre_permis_max: int | None = None

    def to_query_params(self) -> dict[str, str | int | float]:
        """Sérialise vers le format attendu par `requests` : dates en
        AAAA-MM-JJ, listes (`bases`, `champs_supplementaires`) en chaîne
        séparée par des virgules, champs absents omis."""
        query: dict[str, str | int | float] = {}
        for field_name, value in self.model_dump(exclude_none=True).items():
            if isinstance(value, list):
                query[field_name] = ",".join(value)
            elif isinstance(value, datetime.date):
                query[field_name] = value.isoformat()
            else:
                query[field_name] = value
        return query
