"""Génération du jeu de données DEMO, au format pappers_types.ParcelleFiche
(CLAUDE.md, section 8).

Toutes les données produites ici sont FICTIVES (label DEMO_DATA_LABEL,
config.py) : elles ne représentent aucune parcelle, entreprise ou personne
réelle. Le jeu passe ensuite par adapters.py exactement comme les vraies
données Pappers, ce qui garantit que brancher l'API réelle en Phase 3 ne
touche pas au reste du pipeline.

Le jeu inclut volontairement des trous (prix manquants, propriétaires
inconnus, coordonnées absentes, adresses dupliquées) : un jeu de démo trop
propre ne montrerait rien de la gestion des données manquantes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

import config
from src import pappers_types as pt

_RNG = random.Random(config.DEMO_RANDOM_SEED)

RUES = [
    "Rue de la République", "Rue Victor Hugo", "Cours Lafayette", "Rue Garibaldi",
    "Avenue Jean Jaurès", "Rue de Marseille", "Grande Rue", "Rue des Charmettes",
    "Cours Gambetta", "Rue Paul Bert", "Avenue Berthelot", "Rue Servient",
    "Rue Duguesclin", "Place Bellecour", "Rue Moncey", "Avenue Félix Faure",
]

ENSEIGNES_COMMERCE = [
    "Boulangerie Le Fournil", "Pharmacie du Centre", "Café des Sports",
    "Boutique Mode Elegance", "Restaurant Le Gourmet", "Institut Beauté Zen",
    "Librairie Page & Plume", "Épicerie Bio Nature", "Agence Horizon Immobilier",
    "Salon de Coiffure Style", "Fleuriste Les Pétales", "Opticien Vision Plus",
    "Boucherie Charcuterie Dubois", "Pressing Rapide", "Cordonnerie du Marché",
]

# Sections NAF G (commerce, divisions 45-47) et I (hébergement-restauration, 55-56).
NAF_COMMERCE = ["45.20A", "46.31Z", "47.11D", "47.21Z", "47.71Z", "47.29Z", "55.10Z", "56.10A", "56.30Z"]
# Sections NAF C (industrie, 10-33), F (construction, 41-43), H (transport/entreposage, 49-53).
NAF_INDUSTRIEL = ["10.71A", "22.29A", "43.99A", "41.20A", "49.41A", "52.10B", "52.29A"]

ACTIVITES_FONDS_DE_COMMERCE = [
    "Boulangerie-pâtisserie", "Commerce de détail d'habillement", "Restauration traditionnelle",
    "Pharmacie", "Salon de coiffure", "Institut de beauté", "Commerce de détail alimentaire",
]


@dataclass
class OwnerProfile:
    siren: str | None
    nom_entreprise: str
    categorie_juridique: str | None
    activite_principale: str | None
    tranche_effectifs: str | None
    employeur: bool | None
    cessation_activite: bool
    date_creation: date | None
    poids_tirage: int  # plus haut = plus de locaux rattachés (portefeuille plus gros)
    locales: list[tuple[str, str]] = field(default_factory=list)  # (numero_parcelle, adresse) rattachés


def _build_owner_profiles() -> list[OwnerProfile]:
    profils: list[OwnerProfile] = []

    for i in range(10):  # SCI
        profils.append(
            OwnerProfile(
                siren=f"8{i:02d}{_RNG.randint(100000, 999999)}",
                nom_entreprise=f"SCI {_RNG.choice(['DU CENTRE', 'FONCIERE RHONE', 'DES ARCADES', 'SAINT MARTIN', 'DU PARC'])} {i}",
                categorie_juridique="6540",
                activite_principale="68.20B",
                tranche_effectifs=_RNG.choice(["00", "01", None]),
                employeur=_RNG.choice([True, False]),
                cessation_activite=False,
                date_creation=date(_RNG.randint(1995, 2020), _RNG.randint(1, 12), _RNG.randint(1, 28)),
                poids_tirage=_RNG.randint(3, 8),
            )
        )

    for i in range(6):  # sociétés commerciales
        profils.append(
            OwnerProfile(
                siren=f"7{i:02d}{_RNG.randint(100000, 999999)}",
                nom_entreprise=f"{_RNG.choice(['RETAIL', 'COMMERCE', 'DISTRIBUTION'])} {_RNG.choice(['LYON', 'RHONE', 'SUD-EST'])} SAS",
                categorie_juridique=_RNG.choice(["5785", "5710", "5499"]),
                activite_principale=_RNG.choice(["47.19A", "68.32A", "70.22Z"]),
                tranche_effectifs="03",
                employeur=True,
                cessation_activite=_RNG.random() < 0.1,
                date_creation=date(_RNG.randint(1990, 2018), _RNG.randint(1, 12), _RNG.randint(1, 28)),
                poids_tirage=_RNG.randint(2, 6),
            )
        )

    for i in range(4):  # foncières (société + activité 68.xx -> reclassifiée par owner_resolution)
        profils.append(
            OwnerProfile(
                siren=f"6{i:02d}{_RNG.randint(100000, 999999)}",
                nom_entreprise=f"FONCIERE {_RNG.choice(['NATIONALE INVEST', 'COMMERCES DE FRANCE', 'RHONE INVEST'])} {i}",
                categorie_juridique="5785",
                activite_principale="68.20B",
                tranche_effectifs=_RNG.choice(["11", "12"]),
                employeur=True,
                cessation_activite=False,
                date_creation=date(_RNG.randint(1985, 2015), _RNG.randint(1, 12), _RNG.randint(1, 28)),
                poids_tirage=_RNG.randint(8, 15),
            )
        )

    for i in range(3):  # institutionnels (catégorie juridique de droit public, préfixe 7)
        profils.append(
            OwnerProfile(
                siren=f"3{i:02d}{_RNG.randint(100000, 999999)}",
                nom_entreprise=f"OFFICE PUBLIC IMMOBILIER {i}",
                categorie_juridique="7210",
                activite_principale="84.11Z",
                tranche_effectifs="21",
                employeur=True,
                cessation_activite=False,
                date_creation=date(_RNG.randint(1970, 2000), 1, 1),
                poids_tirage=_RNG.randint(6, 12),
            )
        )

    prenoms = ["Jean", "Sophie", "Marc", "Claire", "Philippe"]
    noms = ["Durand", "Martin", "Bernard", "Petit", "Lambert"]
    for i in range(5):  # personnes physiques : pas de siren, pas de categorie_juridique
        profils.append(
            OwnerProfile(
                siren=None,
                nom_entreprise=f"{noms[i].upper()} {prenoms[i].upper()}",
                categorie_juridique=None,
                activite_principale=None,
                tranche_effectifs=None,
                employeur=None,
                cessation_activite=False,
                date_creation=None,
                poids_tirage=_RNG.randint(1, 2),
            )
        )

    for i in range(2):  # catégorie juridique non mappée (branche "autre")
        profils.append(
            OwnerProfile(
                siren=f"9{i:02d}{_RNG.randint(100000, 999999)}",
                nom_entreprise=f"ASSOCIATION FONCIERE {i}",
                categorie_juridique="9220",
                activite_principale="94.99Z",
                tranche_effectifs=None,
                employeur=False,
                cessation_activite=False,
                date_creation=date(2005, 1, 1),
                poids_tirage=1,
            )
        )

    return profils


def _random_adresse(ville_nom: str, code_postal: str, adresses_existantes: list[str]) -> tuple[str, bool]:
    """Retourne (adresse, est_dupliquee). ~6% de chances de dupliquer une
    adresse déjà générée (immeuble avec plusieurs locaux)."""
    if adresses_existantes and _RNG.random() < 0.06:
        return _RNG.choice(adresses_existantes), True
    numero = _RNG.randint(1, 180)
    rue = _RNG.choice(RUES)
    return f"{numero} {rue} {code_postal} {ville_nom.upper()}", False


def _numero_parcelle(code_commune: str, index: int) -> str:
    lettres = "".join(_RNG.choice("ABCDEFGH") for _ in range(2))
    return f"{code_commune}{lettres}{index:04d}"


def _generate_vente(commercial: bool, prix_connu: bool) -> pt.Vente:
    multi_lot = _RNG.random() < 0.1
    surface = round(_RNG.uniform(35, 600) if commercial else _RNG.uniform(200, 3000), 1)
    valeur = round(_RNG.uniform(150_000, 2_200_000), -3) if prix_connu else None
    annee = _RNG.randint(2009, 2024)
    return pt.Vente(
        id=f"demo-{_RNG.randint(100000, 999999)}",
        date=date(annee, _RNG.randint(1, 12), _RNG.randint(1, 28)),
        nature="vente",
        valeur_fonciere=valeur,
        type_local="local_industriel_commercial_ou_assimile",
        surface_reelle_bati=surface,
        nombre_lots=_RNG.randint(2, 4) if multi_lot else 1,
        lots=None,
    )


def _generate_locale(index: int, ville: tuple[str, str, str, str, str], adresses_existantes: list[str]) -> tuple[pt.ParcelleFiche, str | None]:
    """Retourne (fiche, siren_attribue_ou_None)."""
    nom, code_commune, code_postal, departement, code_departement = ville
    adresse, _dupliquee = _random_adresse(nom, code_postal, adresses_existantes)
    numero_parcelle = _numero_parcelle(code_commune, index)

    # Répartition des profils d'actif : commercial clair / industriel-entrepôt
    # clair / ambigu / hors périmètre (résidentiel).
    tirage = _RNG.random()
    if tirage < 0.55:
        profil = "commercial"
    elif tirage < 0.75:
        profil = "industriel"
    elif tirage < 0.93:
        profil = "ambigu"
    else:
        profil = "hors_perimetre"

    coordonnees_connues = _RNG.random() > 0.10
    top_left = bottom_right = geometrie = None
    if coordonnees_connues:
        lat = 45.75 + _RNG.uniform(-0.08, 0.08)
        lon = 4.83 + _RNG.uniform(-0.08, 0.08)
        top_left = pt.LatLon(lat=lat + 0.0004, lon=lon - 0.0004)
        bottom_right = pt.BottomRight(latitude=lat - 0.0004, longitude=lon + 0.0004)
        geometrie = pt.Geometrie(type="Polygon", coordinates=[[[lon, lat]]])

    ventes: list[pt.Vente] = []
    batiments: list[pt.Batiment] = []
    occupants: list[pt.Occupant] = []
    fonds_de_commerce: list[pt.FondsDeCommerce] = []
    permis: list[pt.Permis] = []

    if profil == "hors_perimetre":
        ventes.append(
            pt.Vente(
                date=date(_RNG.randint(2010, 2023), 1, 1),
                nature="vente",
                valeur_fonciere=round(_RNG.uniform(80_000, 400_000), -3),
                type_local=_RNG.choice(["appartement", "maison", "dependance"]),
                surface_reelle_bati=round(_RNG.uniform(20, 120), 1),
                nombre_lots=1,
            )
        )
    else:
        prix_connu = _RNG.random() > 0.15  # ~15% de prix manquants (trou volontaire)
        vente = _generate_vente(commercial=(profil != "industriel"), prix_connu=prix_connu)
        ventes.append(vente)
        if _RNG.random() < 0.15:  # mutation supplémentaire ancienne (signal mutations multiples)
            ventes.append(_generate_vente(commercial=(profil != "industriel"), prix_connu=True))

        if profil == "commercial":
            usage, nature = "commercial_et_services", "industriel_agricole_ou_commercial"
        elif profil == "industriel":
            usage, nature = _RNG.choice(["industriel", "agricole"]), _RNG.choice(["industriel_agricole_ou_commercial", "silo"])
        else:  # ambigu
            usage, nature = _RNG.choice(["indifferencie", "tertiaire_et_autres", None]), None

        batiments.append(
            pt.Batiment(
                parcelle_principale=True,
                usages=usage,
                natures=nature,
                surface=vente.surface_reelle_bati,
                annee_construction=_RNG.randint(1930, 2015),
            )
        )

        if profil in ("commercial", "ambigu") and _RNG.random() < 0.8:
            enseigne = _RNG.choice(ENSEIGNES_COMMERCE) if profil == "commercial" else None
            naf = _RNG.choice(NAF_COMMERCE) if profil == "commercial" else _RNG.choice(NAF_COMMERCE + NAF_INDUSTRIEL)
            date_sortie = None
            ferme = False
            if _RNG.random() < 0.15:  # occupant parti (signal)
                date_sortie = date(_RNG.randint(2022, 2025), _RNG.randint(1, 12), 1)
                ferme = _RNG.random() < 0.5
            occupants.append(
                pt.Occupant(
                    siren=f"{_RNG.randint(100000000, 999999999)}",
                    siret=f"{_RNG.randint(10000000000000, 99999999999999)}",
                    fiabilite_appartenance_parcelle=_RNG.choice(["haute", "moyenne", "faible"]),
                    date_entree_lieux=date(_RNG.randint(2005, 2022), 1, 1),
                    activite_principale_etablissement=naf,
                    enseigne=enseigne,
                    cessation_activite=False,
                    etablissement_ferme=ferme,
                    date_sortie_lieux=date_sortie,
                    nom_entreprise=enseigne or "Occupant inconnu",
                )
            )
        elif profil == "industriel" and _RNG.random() < 0.6:
            occupants.append(
                pt.Occupant(
                    siren=f"{_RNG.randint(100000000, 999999999)}",
                    fiabilite_appartenance_parcelle=_RNG.choice(["haute", "moyenne"]),
                    date_entree_lieux=date(_RNG.randint(2005, 2022), 1, 1),
                    activite_principale_etablissement=_RNG.choice(NAF_INDUSTRIEL),
                    enseigne=None,
                    nom_entreprise="Exploitant industriel",
                )
            )

        if profil == "commercial" and _RNG.random() < 0.4:
            annonce = None
            precedent = None
            if _RNG.random() < 0.3:
                annonce = pt.AnnonceBodacc(numero=_RNG.randint(1, 999), date=date(_RNG.randint(2018, 2024), 1, 1))
                precedent = pt.TiersFondsDeCommerce(
                    siren=f"{_RNG.randint(100000000, 999999999)}", nom_entreprise="Ancien exploitant", cessation_activite=True
                )
            fonds_de_commerce.append(
                pt.FondsDeCommerce(
                    activite=_RNG.choice(ACTIVITES_FONDS_DE_COMMERCE),
                    prix=round(_RNG.uniform(30_000, 250_000), -3),
                    date_debut_activite=date(_RNG.randint(2005, 2022), 1, 1),
                    annonce_bodacc=annonce,
                    precedent_proprietaire=precedent,
                    fiabilite_appartenance_parcelle=_RNG.choice(["haute", "moyenne", "faible"]),
                )
            )

        if _RNG.random() < 0.1:
            permis.append(
                pt.Permis(
                    numero=f"P{_RNG.randint(1000, 9999)}",
                    etat="autorise",
                    type="permis_de_construire_locaux",
                    date_autorisation=date(_RNG.randint(2023, 2025), _RNG.randint(1, 12), 1),
                )
            )

    fiche = pt.ParcelleFiche(
        numero=numero_parcelle,
        adresse=adresse,
        code_commune=code_commune,
        commune=nom,
        code_departement=code_departement,
        departement=departement,
        codes_postaux=[code_postal],
        contenance=round(_RNG.uniform(80, 3000), 0),
        arpente=_RNG.choice([True, False]),
        top_left=top_left,
        bottom_right=bottom_right,
        geometrie=geometrie,
        ventes=ventes,
        batiments=batiments,
        occupants=occupants,
        fonds_de_commerce=fonds_de_commerce,
        permis=permis,
        proprietaires=[],  # rattaché ensuite dans generate_demo_parcelles
    )
    return fiche, adresse


def generate_demo_parcelles() -> list[pt.ParcelleFiche]:
    """Génère le jeu DEMO complet : ~130 locaux, 4-5 villes, ~30
    propriétaires (dont plusieurs multi-actifs), avec trous volontaires.

    Reseed à chaque appel : le jeu généré est déterministe (utile pour des
    captures d'écran ou une démo stable), y compris sur des appels répétés
    au sein du même processus."""
    _RNG.seed(config.DEMO_RANDOM_SEED)
    profils = _build_owner_profiles()
    fiches: list[pt.ParcelleFiche] = []
    adresses_generees: list[str] = []

    poids = [p.poids_tirage for p in profils]

    for index in range(config.DEMO_NB_LOCAUX):
        ville = _RNG.choice(config.DEMO_VILLES)
        fiche, adresse = _generate_locale(index, ville, adresses_generees)
        if adresse:
            adresses_generees.append(adresse)

        # ~10% des locaux sans propriétaire identifié (trou volontaire).
        if _RNG.random() < 0.10:
            fiches.append(fiche)
            continue

        proprietaire_profil = _RNG.choices(profils, weights=poids, k=1)[0]
        proprietaire_profil.locales.append((fiche.numero, fiche.adresse))
        fiches.append(fiche)

    # Deuxième passe : construit le Proprietaire (avec locaux/parcelles
    # déclarés = portefeuille complet de ce propriétaire dans le jeu DEMO,
    # éventuellement complété de quelques références "fantômes" pour
    # illustrer un portefeuille API plus large que ce qui est ingéré) et
    # l'attache à la fiche correspondante.
    fiche_par_numero = {f.numero: f for f in fiches}
    for profil in profils:
        if not profil.locales:
            continue
        locaux_api = [
            pt.ProprietaireLocal(numero_parcelle=num, adresse=adr) for num, adr in profil.locales
        ]
        if len(profil.locales) >= 4 and _RNG.random() < 0.4:
            for _ in range(_RNG.randint(1, 2)):
                locaux_api.append(
                    pt.ProprietaireLocal(
                        numero_parcelle=_numero_parcelle(config.DEMO_VILLES[0][1], _RNG.randint(9000, 9999)),
                        adresse="Local non présent dans le périmètre ingéré",
                    )
                )

        proprietaire = pt.Proprietaire(
            siren=profil.siren,
            date_creation=profil.date_creation,
            nom_entreprise=profil.nom_entreprise,
            tranche_effectifs=profil.tranche_effectifs,
            categorie_juridique=profil.categorie_juridique,
            activite_principale=profil.activite_principale,
            employeur=profil.employeur,
            cessation_activite=profil.cessation_activite,
            locaux=locaux_api,
        )
        for numero, _adresse in profil.locales:
            fiche_par_numero[numero].proprietaires.append(proprietaire)

    return fiches
