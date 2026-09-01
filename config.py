"""Configuration centrale : coefficients de scoring, seuils, mappings.

Toute valeur numérique utilisée par le scoring ou la qualification des
actifs doit vivre ici, jamais codée en dur ailleurs (voir CLAUDE.md, règle 6).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Version de la configuration de scoring.
# Incrémenter à chaque changement de coefficient : permet de savoir avec
# quels réglages un score en base a été calculé (voir scores.config_version).
# ---------------------------------------------------------------------------
CONFIG_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Source de données et connexion
# ---------------------------------------------------------------------------
DATA_SOURCE = os.getenv("DATA_SOURCE", "demo")  # "demo" ou "pappers"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://localhost/broker_immo")
PAPPERS_IMMO_API_KEY = os.getenv("PAPPERS_IMMO_API_KEY", "")
PAPPERS_IMMO_BASE_URL = "https://api-immobilier.pappers.fr/v1/"

# Réglages du client HTTP (src/pappers_immo_client.py) : propres à notre
# implémentation, pas des valeurs documentées par l'API (rien à voir avec
# la règle 1 sur les champs/endpoints Pappers).
PAPPERS_IMMO_TIMEOUT_SECONDS = float(os.getenv("PAPPERS_IMMO_TIMEOUT_SECONDS", "10"))
PAPPERS_IMMO_MAX_RETRIES = int(os.getenv("PAPPERS_IMMO_MAX_RETRIES", "3"))
PAPPERS_IMMO_RETRY_BACKOFF_SECONDS = float(os.getenv("PAPPERS_IMMO_RETRY_BACKOFF_SECONDS", "1"))

# ---------------------------------------------------------------------------
# Cache Postgres et crédits API (section 3.8 du cahier des charges)
# ---------------------------------------------------------------------------
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "30"))
MAX_CREDITS_PER_RUN = int(os.getenv("MAX_CREDITS_PER_RUN", "500"))

# Coût en jetons des champs supplémentaires (section 3.8 de la spec API).
# champs_supplementaires=tous ne doit jamais être utilisé.
#
# TODO(V3) : la spec (api_1.0.0.yaml) et le cahier des charges ne
# documentent que ce surcoût par champ supplémentaire, jamais le coût de
# base d'une requête /parcelles sans aucun champ supplémentaire. Le
# compteur de jetons de PappersImmoClient (`credits_used`) ne comptabilise
# donc que ces surcoûts documentés et SOUS-ESTIME la consommation réelle
# tant que ce coût de base n'est pas confirmé (documentation Pappers à
# jour, ou exemple de facturation réelle). Ne pas ajouter de constante de
# coût de base ici sans cette confirmation (règle 1, CLAUDE.md).
CHAMPS_SUPPLEMENTAIRES_COUTS = {
    "tous": 3,
    "bounding_box": 1,
    "arpente": 0,
    "adresse": 1,
    "ventes.code_type_local": 0,
    "ventes.nature_culture": 0,
    "ventes.ancienne_parcelle_cadastrale": 0,
    "proprietaires.parcelles": 1,
    "proprietaires.personnes_physiques": 1,
    "proprietaires.representants_personnes_morales": 1,
    "occupants.categorie_juridique": 0,
    "permis.zone_operatoire": 0,
    "permis.complet": 1,
}

# Champs supplémentaires demandés par défaut lors de l'ingestion.
# Volontairement minimal : le strict nécessaire au scoring et à
# l'affichage (règle 3.8 : ne jamais utiliser "tous").
# proprietaires.personnes_physiques n'est PAS demandé par défaut (données
# sensibles de bénéficiaires effectifs, voir section 3.4).
DEFAULT_CHAMPS_SUPPLEMENTAIRES = [
    "arpente",
    "adresse",
    "bounding_box",
    "proprietaires.parcelles",
    "occupants.categorie_juridique",
]

# Bases demandées par défaut lors de l'ingestion (paramètre `bases` de
# /parcelles). Limité à ce que `src/adapters.py` consomme réellement :
# `dpe` et `coproprietes` ne sont utilisées par aucun critère de
# qualification ou de scoring en V1, donc jamais demandées par défaut
# (même logique que pour champs_supplementaires : ne demander que le
# strict nécessaire, section 3.8).
DEFAULT_BASES_INGESTION = [
    "proprietaires",
    "ventes",
    "batiments",
    "occupants",
    "permis",
    "fonds_de_commerce",
]

# ---------------------------------------------------------------------------
# Fiabilité API -> confidence_score (section 3.5)
# Mapping direct de l'énumération fiabilite_appartenance_parcelle
# (Occupant, FondsDeCommerce). Ne jamais remplacer par une heuristique maison.
# ---------------------------------------------------------------------------
FIABILITE_TO_CONFIDENCE_SCORE = {
    "haute": 100,
    "moyenne": 75,
    "faible": 50,
    "absente": 25,  # champ fiabilite_appartenance_parcelle présent mais vide
    None: 0,  # aucune donnée de fiabilité disponible du tout
}

# ---------------------------------------------------------------------------
# Départements sans données de mutation DVF (section 3.6)
# ---------------------------------------------------------------------------
DEPARTEMENTS_SANS_DVF = {"67", "68", "57", "976"}  # Bas-Rhin, Haut-Rhin, Moselle, Mayotte

# ---------------------------------------------------------------------------
# Qualification "local commercial" par faisceau d'indices (section 3.3,
# src/asset_typing.py). Chaque indice contribue un score signé ; le total
# détermine le type_actif retenu et sa confiance.
# ---------------------------------------------------------------------------
ASSET_TYPING_USAGE_BATIMENT_POSITIF = {"commercial_et_services"}
ASSET_TYPING_USAGE_BATIMENT_NEGATIF = {"industriel", "agricole"}
ASSET_TYPING_NATURE_BATIMENT_POSITIF = {"industriel_agricole_ou_commercial"}
ASSET_TYPING_NATURE_BATIMENT_NEGATIF = {"silo"}

# Sections NAF Rev2 (nomenclature INSEE, référencée par l'API Pappers pour
# code_naf_occupant/proprietaire). Divisions -> section, limitées aux
# sections utiles à la qualification commerciale (positives : G, I ;
# négatives : C, F, H).
NAF_SECTION_POSITIVE = {"G", "I"}
NAF_SECTION_NEGATIVE = {"C", "F", "H"}
NAF_DIVISION_TO_SECTION = {
    **{str(d): "C" for d in range(10, 34)},  # industrie manufacturière
    **{str(d): "F" for d in range(41, 44)},  # construction
    **{str(d): "G" for d in range(45, 48)},  # commerce
    **{str(d): "H" for d in range(49, 54)},  # transports et entreposage
    **{str(d): "I" for d in (55, 56)},  # hébergement et restauration
}

# Poids des indices dans le score de qualification (positif = commerce,
# négatif = industriel/entrepôt). Le total est comparé aux seuils
# ASSET_TYPING_SEUIL_* pour déterminer type_actif_confidence.
ASSET_TYPING_POIDS = {
    "type_local_vente_ok": 1,
    "usage_batiment_positif": 3,
    "usage_batiment_negatif": -4,
    "nature_batiment_positif": 2,
    "nature_batiment_negatif": -4,
    "fonds_de_commerce_present": 5,
    "naf_occupant_positif": 3,
    "naf_occupant_negatif": -4,
    "enseigne_presente": 2,
    "surface_coherente_commerce": 1,
}

# Surface de bâti jugée cohérente avec du commerce de pied d'immeuble
# plutôt que de la logistique/entrepôt (indice 7, section 3.3).
ASSET_TYPING_SURFACE_COMMERCE_MAX_M2 = 1000

# Seuils de décision sur le score d'indices cumulé.
ASSET_TYPING_SEUIL_HAUTE_CONFIANCE = 5
ASSET_TYPING_SEUIL_CONFIANCE_MOYENNE = 2
# En dessous de ASSET_TYPING_SEUIL_CONFIANCE_MOYENNE : confiance "faible".
# Un score trop négatif (< ASSET_TYPING_SEUIL_EXCLUSION) indique un local
# manifestement industriel/entrepôt plutôt qu'un commerce incertain.
ASSET_TYPING_SEUIL_EXCLUSION = -4

# ---------------------------------------------------------------------------
# Typologie de propriétaire (section 6, table properties/owners)
# Dérivée de categorie_juridique (nomenclature INSEE 2028129, référencée par
# l'API) et, en complément, de activite_principale (NAF).
# ---------------------------------------------------------------------------
CATEGORIE_JURIDIQUE_TO_TYPE_PROPRIETAIRE = {
    "6540": "sci",
    "6541": "sci",  # SCI d'attribution
    "1000": "personne_physique",
    "5202": "societe",  # SARL unipersonnelle
    "5498": "societe",  # EURL
    "5499": "societe",  # SARL
    "5710": "societe",  # SA à conseil d'administration
    "5720": "societe",  # SASU
    "5785": "societe",  # SAS
    "5800": "societe",  # SE
}
# Divisions NAF (activite_principale) associées aux foncières / activités
# immobilières : reclassifie une société en "fonciere" plutôt que "societe".
NAF_DIVISIONS_FONCIERE = {"68"}
# Catégories juridiques de droit public (nomenclature INSEE, préfixe 7).
CATEGORIE_JURIDIQUE_PREFIXE_INSTITUTIONNEL = ("7",)

# ---------------------------------------------------------------------------
# Scoring — Asset Score (40 points), section 7
# ---------------------------------------------------------------------------
ASSET_SCORE_MAX = 40
ASSET_SCORE_VALEUR_MAX = 10
ASSET_SCORE_SURFACE_MAX = 5
ASSET_SCORE_PRIX_M2_MAX = 10
ASSET_SCORE_LOCALISATION_MAX = 15

# Fourchette de prix cible pour le critère "Valeur" : score maximal si
# prix_derniere_mutation est dans [MIN, MAX], décroît linéairement en
# dehors jusqu'à 0 à +/-50%. 0 si le prix est inconnu.
ASSET_VALEUR_CIBLE_MIN = 150_000
ASSET_VALEUR_CIBLE_MAX = 1_500_000
ASSET_VALEUR_TOLERANCE_RATIO = 0.5  # score nul au-delà de +/-50% de la cible

# Fourchette de surface cible (m²) pour le critère "Surface".
ASSET_SURFACE_CIBLE_MIN = 50
ASSET_SURFACE_CIBLE_MAX = 400
ASSET_SURFACE_TOLERANCE_RATIO = 0.5

# Critère "Prix/m²" : comparé aux mutations comparables de la même commune
# et du même type_actif dans la base. Hypothèse de sourcing retenue (à
# confirmer avec le métier) : un actif décoté par rapport à ses comparables
# est une opportunité d'acquisition plus intéressante, donc mieux noté.
# Score maximal si prix_m2 <= médiane_comparables * (1 - DECOTE_MAX_RATIO),
# score nul si prix_m2 >= médiane_comparables * (1 + PRIME_MAX_RATIO).
# 0 si prix_m2_fiable est faux ou s'il y a moins de MIN_COMPARABLES pairs.
ASSET_PRIX_M2_DECOTE_MAX_RATIO = 0.30
ASSET_PRIX_M2_PRIME_MAX_RATIO = 0.30
ASSET_PRIX_M2_MIN_COMPARABLES = 3

# Critère "Localisation" (0-15) : AUCUNE donnée d'emplacement qualitatif
# (zone commerçante, flux piéton, niveau de loyer de rue) n'est disponible
# dans l'API Pappers Immobilier en V1. Le score est donc toujours 0 pour
# l'instant, conformément à la règle "0 si la qualification d'emplacement
# n'est pas disponible" (section 7). TODO(V2) : brancher une source de
# qualité d'emplacement (ex. données de flux, indice de loyers commerciaux)
# avant d'activer ce critère.
ASSET_LOCALISATION_DISPONIBLE = False

# ---------------------------------------------------------------------------
# Scoring — Owner Score (30 points), section 7
# ---------------------------------------------------------------------------
OWNER_SCORE_MAX = 30
OWNER_SCORE_PORTEFEUILLE_MAX = 15
OWNER_SCORE_TYPOLOGIE_MAX = 15

# Taille du portefeuille IDENTIFIÉ DANS NOTRE BASE (jamais le portefeuille
# API déclaré, voir section 3.4 / 7).
OWNER_PORTEFEUILLE_BAREME = (
    # (borne_inf_incluse, borne_sup_incluse_ou_None, points)
    (1, 1, 0),
    (2, 5, 5),
    (6, 10, 10),
    (11, None, 15),
)

# Coefficients par type_proprietaire, sur OWNER_SCORE_TYPOLOGIE_MAX points.
# Une foncière/investisseur institutionnel gère un portefeuille de manière
# plus prévisible/professionnelle qu'un particulier : coefficient plus haut.
TYPE_PROPRIETAIRE_COEFFICIENTS = {
    "fonciere": 15,
    "institutionnel": 15,
    "sci": 10,
    "societe": 8,
    "exploitant": 5,
    "personne_physique": 5,
    "autre": 3,
    "inconnu": 0,
}

# ---------------------------------------------------------------------------
# Scoring — Sell Signal Score (30 points), section 7
# ---------------------------------------------------------------------------
SELL_SIGNAL_SCORE_MAX = 30

# Poids par signal (somme <= SELL_SIGNAL_SCORE_MAX ; le total est plafonné
# à SELL_SIGNAL_SCORE_MAX dans scoring.py).
SELL_SIGNAL_POIDS = {
    "mutation_ancienne": 6,  # dernière vente > SELL_SIGNAL_MUTATION_ANCIENNE_ANS
    "mutations_multiples": 4,  # nombre_ventes >= 2 sur la parcelle
    "cession_recente_portefeuille": 5,  # une autre parcelle du même siren_proprietaire a muté récemment
    "fonds_de_commerce_cede": 5,  # annonce_bodacc / precedent_proprietaire renseignés
    "occupant_parti": 4,  # date_sortie_lieux renseignée ou etablissement_ferme
    "proprietaire_cessation_activite": 3,  # owners.cessation_activite
    "permis_recent": 2,  # permis récent sur la parcelle
    "gros_portefeuille_declare": 1,  # portefeuille API déclaré important
}

SELL_SIGNAL_MUTATION_ANCIENNE_ANS = 8
SELL_SIGNAL_CESSION_RECENTE_MOIS = 24
SELL_SIGNAL_PERMIS_RECENT_ANS = 2
SELL_SIGNAL_GROS_PORTEFEUILLE_SEUIL = 10  # locaux/parcelles déclarés par l'API

# ---------------------------------------------------------------------------
# Explications — liste noire de vocabulaire (section 7, non négociable)
# Un test (tests/test_explanations.py) échoue si un terme de cette liste
# apparaît dans un texte généré par explanations.py.
# ---------------------------------------------------------------------------
EXPLANATION_VOCABULAIRE_INTERDIT = [
    "veut vendre",
    "veut céder",
    "souhaite vendre",
    "souhaite céder",
    "cherche à vendre",
    "cherche à céder",
    "va vendre",
    "va céder",
    "est vendeur",
    "est vendeuse",
    "propriétaire vendeur",
    "en vente",
    "à vendre",
]

# ---------------------------------------------------------------------------
# Mode DEMO (section 8)
# ---------------------------------------------------------------------------
DEMO_DATA_LABEL = "DEMO DATA — NOT REAL"
DEMO_NB_LOCAUX = 130
DEMO_NB_PROPRIETAIRES = 30
DEMO_VILLES = [
    # (nom, code_commune, code_postal, departement, code_departement)
    ("Lyon", "69386", "69003", "Rhône", "69"),
    ("Villeurbanne", "69266", "69100", "Rhône", "69"),
    ("Bron", "69029", "69500", "Rhône", "69"),
    ("Vénissieux", "69259", "69200", "Rhône", "69"),
    ("Saint-Priest", "69290", "69800", "Rhône", "69"),
]
DEMO_RANDOM_SEED = 42
