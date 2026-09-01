# Commercial Real Estate Sourcing Engine — CLAUDE.md

## 1. Contexte et objectif

Tu construis un prototype d'application de sourcing d'immobilier commercial en France.

À partir d'une zone géographique, l'application doit produire un classement des 100 locaux commerciaux les plus intéressants à prospecter, avec pour chacun le propriétaire identifié, un score de priorité décomposé, et une explication lisible du score.

Le livrable est un **prototype professionnel démontrable en entretien** pour un poste d'Analyste Sourcing. La priorité est, dans cet ordre :

**fonctionnement → fiabilité des données → explicabilité du scoring → interface → sophistication IA.**

L'application doit tourner de bout en bout sans clé API, en mode DEMO.

---

## 2. Règles permanentes

Ces règles s'appliquent à chaque phase, sans exception.

1. **Ne jamais inventer un endpoint, un paramètre ou un champ de l'API Pappers.** Si une information manque, crée une abstraction propre, laisse un `TODO` explicite et demande la documentation ou un exemple de réponse brute. Ne devine pas.
2. **Ne jamais inventer une donnée immobilière.** Pas de coordonnées GPS estimées, pas de prix extrapolé, pas de propriétaire déduit sans source. Une donnée absente est `NULL` et doit être affichée comme manquante.
3. **Ne jamais présenter une donnée incertaine comme un fait.** Toute association propriété↔propriétaire porte une source, un `confidence_score` et une date de vérification.
4. **Ne jamais écrire une clé API dans le code.** Tout passe par `.env`, avec un `.env.example` versionné et un `.gitignore` correct.
5. **Conserver la donnée brute.** Le nettoyage crée une valeur normalisée à côté de la valeur source, il ne l'écrase jamais. Les payloads API sont stockés tels quels en JSONB.
6. **Centraliser les coefficients** dans `config.py`. Aucune valeur de scoring codée en dur ailleurs.
7. **Code lisible par un développeur Python junior/intermédiaire.** Type hints, docstrings courtes, pas d'abstraction prématurée, pas de métaprogrammation.
8. **Construire progressivement.** Avant chaque phase : inspecter l'existant, expliquer en quelques lignes ce qui va être créé, coder, lancer les tests, corriger, vérifier que l'app démarre. **Puis s'arrêter et attendre la validation.** Ne jamais générer plusieurs phases d'un coup.

---

## 3. L'API Pappers Immobilier — spécification réelle

Basé sur la spec OpenAPI 1.0.0 fournie (`docs/api_1_0_0.yaml`). Base URL : `https://api-immobilier.pappers.fr/v1/`. Authentification par header `api-key` (le paramètre query `api_token` est déconseillé).

### 3.1 Deux endpoints, soixante-seize filtres

Toute l'API tient en deux routes :

| Route | Usage |
|---|---|
| `GET /parcelles` | Recherche multi-critères de parcelles |
| `GET /parcelles/{numero_parcelle}` | Fiche d'une parcelle précise |

Il n'existe pas de route `/proprietaires`, `/ventes` ou `/locaux`. Les données associées s'obtiennent via le paramètre `bases`, qui accepte une liste séparée par des virgules :

`proprietaires` · `ventes` · `batiments` · `dpe` · `occupants` · `permis` · `fonds_de_commerce` · `coproprietes`

Sans `bases`, seules les informations de la parcelle sont retournées. La réponse est une `ParcelleFiche` = `ParcelleBase` + un tableau par base demandée.

### 3.2 Le filtrage se fait côté serveur

Les 76 paramètres de `/parcelles` permettent de cibler la requête. Ceux qui structurent le projet :

**Zone** — `code_postal`, `code_commune`, `departement`, `region`, `adresse`, ou `latitude` + `longitude` + `distance`. Le rayon autour d'une adresse, prévu en V2 dans le cahier des charges initial, est donc disponible dès la V1.

**Actif** — `type_local_vente`, `prix_vente_min/max`, `surface_bati_vente_min/max`, `date_vente_min/max`, `nature_vente`, `nombre_ventes_min/max`, `usage_batiment`, `nature_batiment`, `surface_batiment_min/max`, `annee_construction_batiment_min/max`.

**Propriétaire** — `siren_proprietaire`, `categorie_juridique_proprietaire`, `code_naf_proprietaire`, `denomination_proprietaire`, `nombre_proprietaires_min/max`, `tranche_effectif_proprietaire_min/max`.

**Occupant** — `siren_occupant`, `code_naf_occupant`, `denomination_occupant`, `categorie_juridique_occupant`.

**Fonds de commerce** — `prix_fonds_de_commerce_min/max`, `date_fonds_de_commerce_min/max`, `code_naf_fonds_de_commerce`, `nombre_fonds_de_commerce_min/max`.

Un `ParcelleSearchParams` Pydantic couvre ces paramètres, et les filtres de l'interface correspondent aux filtres API quand la requête est lancée sur une nouvelle zone. Les filtres appliqués après coup sur la base restent utiles pour l'exploration des résultats déjà rapatriés.

### 3.3 Le problème central du projet : « local commercial » n'est pas filtrable directement

`type_local_vente` n'a que quatre valeurs, héritées de DVF :

`appartement` · `maison` · `dependance` · `local_industriel_commercial_ou_assimile`

La quatrième **confond commerce, industrie, entrepôt et assimilés**. Le cahier des charges demande d'exclure les entrepôts et locaux industriels : ce n'est pas faisable avec ce seul filtre.

C'est le cœur technique du projet, et ce qu'il faut savoir expliquer. La qualification « local commercial » est reconstruite par faisceau d'indices, dans un module dédié `src/asset_typing.py` :

1. `type_local_vente = local_industriel_commercial_ou_assimile` comme filtre de premier niveau ;
2. `usage_batiment` = `commercial_et_services` (indice positif fort) contre `industriel` ou `agricole` (indice négatif fort) ;
3. `nature_batiment` = `industriel_agricole_ou_commercial` contre `silo` (négatif) ;
4. présence d'un `fonds_de_commerce` sur la parcelle (indice positif très fort) ;
5. `code_naf_occupant` en section G (commerce) ou I (hébergement-restauration) contre sections C, F, H (industrie, construction, transport-logistique) ;
6. `enseigne` renseignée sur l'occupant (indice positif) ;
7. `surface_bati` cohérente avec du commerce de pied d'immeuble plutôt qu'avec de la logistique.

La sortie n'est pas un booléen mais un couple `(type_actif, type_actif_confidence)` avec la liste des indices retenus. Cette liste est affichée dans la fiche actif. Un actif de type incertain n'est pas exclu : il est classé avec une confiance basse et l'interface le signale.

### 3.4 Les propriétaires sont déjà enrichis — Pappers Entreprises devient optionnel

Le schéma `Proprietaire` retourné par `bases=proprietaires` contient déjà : `siren`, `nom_entreprise`, `categorie_juridique`, `activite_principale`, `date_creation`, `tranche_effectifs`, `annee_effectifs`, `employeur`, `cessation_activite`.

Et surtout deux tableaux décisifs pour le regroupement de portefeuille :

- `locaux` — les locaux du propriétaire, avec adresse, bâtiment, niveau, porte ;
- `parcelles` — les parcelles du propriétaire, avec commune et département, disponible via `champs_supplementaires=proprietaires.parcelles`.

Autrement dit, **le portefeuille d'un propriétaire est fourni par l'API**, il n'est pas seulement reconstruit depuis notre base. Il faut distinguer clairement les deux dans le modèle et dans l'interface : « portefeuille déclaré par l'API » et « actifs présents dans notre base ». Ne jamais les additionner.

Deux champs supplémentaires payants complètent le tableau : `proprietaires.personnes_physiques` (bénéficiaires effectifs, dirigeants, dates de naissance, parts détenues) et `proprietaires.representants_personnes_morales`.

Conséquence sur l'architecture : **Pappers Entreprises n'est pas nécessaire en V1.** Ne pas l'implémenter. `pappers_entreprises_client.py` reste un fichier vide avec un docstring expliquant qu'il servira en V2 pour les comptes annuels et le BODACC. Une seule clé API en V1 :

```
PAPPERS_IMMO_API_KEY=...
```

Sur les personnes physiques : les données de bénéficiaires effectifs sont sensibles et l'accès est encadré. En V1, ce champ supplémentaire n'est pas demandé par défaut. Le prototype se concentre sur les personnes morales, ce qui correspond de toute façon à la cible (SCI, foncières, sociétés).

### 3.5 La fiabilité est fournie par l'API — ne pas l'inventer

Les schémas `Occupant` et `FondsDeCommerce` portent un champ `fiabilite_appartenance_parcelle` avec l'énumération `faible` / `moyenne` / `haute`.

C'est la source réelle du `confidence_score` du cahier des charges. Elle est mappée directement plutôt que d'inventer une heuristique :

`haute` → 100 · `moyenne` → 75 · `faible` → 50 · absente → 25 · pas de donnée → 0

Le mapping vit dans `config.py`. Une valeur d'origine API est toujours conservée à côté du score normalisé.

### 3.6 Sémantique du prix

Les prix viennent de DVF, via le champ `valeur_fonciere` du schéma `Vente`. C'est un **prix de mutation historique**, pas une valeur de marché. Un local vendu 800 k€ en 2015 n'a pas de prix aujourd'hui.

- le champ s'appelle `prix_derniere_mutation`, jamais `prix` ni `valeur` ;
- l'interface affiche toujours la date à côté du prix ;
- attention à `valeur_fonciere` sur les ventes multi-lots : `nombre_lots` et `lots` sont renseignés, et le prix porte sur l'ensemble de la mutation. Ne pas calculer de prix/m² sur une mutation multi-lots sans le signaler, c'est une source classique d'aberrations dans DVF ;
- un actif sans mutation connue a `prix = NULL`, reste dans la base, obtient 0 sur les critères de valeur, et l'explication le dit ;
- une valeur réindexée, si elle est ajoutée, vit dans une colonne séparée avec sa méthode.

Limite connue : la DGFiP ne fournit pas les mutations pour le Bas-Rhin, le Haut-Rhin, la Moselle et Mayotte. À afficher dans l'interface si la zone sélectionnée est concernée.

### 3.7 Coordonnées

`ParcelleBase` fournit `geometrie`, `top_left` et `bottom_right`. Les coordonnées sont donc réelles — aucune raison d'en inventer. `bounding_box` et `adresse` coûtent 1 jeton supplémentaire chacun ; `arpente` est gratuit.

### 3.8 Crédits et pagination — contrainte d'architecture

Facturation à la requête, avec surcoût par champ supplémentaire : `tous` +3 jetons, `bounding_box` +1, `adresse` +1, `proprietaires.parcelles` +1, `proprietaires.personnes_physiques` +1, `proprietaires.representants_personnes_morales` +1, `permis.complet` +1. Sont gratuits : `arpente`, `ventes.code_type_local`, `ventes.nature_culture`, `ventes.ancienne_parcelle_cadastrale`, `occupants.categorie_juridique`, `permis.zone_operatoire`.

Ne jamais utiliser `champs_supplementaires=tous`. Demander explicitement le strict nécessaire, listé dans `config.py`.

Pagination : `page` est plafonnée à 400 résultats. Pour un balayage complet de zone, utiliser le curseur — `curseur=*` à la première requête, puis la valeur `curseurSuivant` de la réponse précédente. `par_page` vaut 10 par défaut, à monter.

Architecture qui en découle :

- **PostgreSQL est un cache**, pas un simple stockage. Toute réponse est persistée avec son horodatage ; une parcelle déjà en base n'est pas réinterrogée avant expiration (TTL configurable, 30 jours par défaut).
- **L'ingestion est un script batch** : `python -m src.ingest --code-postal 69002`. Jamais déclenchée depuis Streamlit.
- **Streamlit ne lit que la base.** Aucun appel API dans `ui/`.
- Le client tient un compteur de jetons consommés par run, l'affiche en fin d'ingestion, et s'arrête proprement au-delà de `MAX_CREDITS_PER_RUN`.
- Un mode `--dry-run` estime le coût en jetons avant de lancer l'ingestion réelle.

## 4. Stack

Python 3.11+ · PostgreSQL · SQLAlchemy 2.0 · Alembic · Pandas · Pydantic v2 · Streamlit · Plotly · Requests · python-dotenv · pytest · Git.

Pas de Cloudflare en V1. Pas de machine learning en V1. L'architecture doit permettre de remplacer Streamlit sans toucher à `src/`.

---

## 5. Architecture

```text
Broker Immo/
├── app.py                      # point d'entrée Streamlit, routing entre pages
├── config.py                   # tous les coefficients et seuils
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── alembic/
├── src/
│   ├── models.py               # modèles SQLAlchemy
│   ├── schemas.py              # modèles Pydantic du domaine (couche pivot)
│   ├── database.py             # session, engine, helpers
│   ├── pappers_immo_client.py  # auth, retry, timeout, curseur, compteur jetons
│   ├── pappers_entreprises_client.py  # vide en V1, docstring V2
│   ├── pappers_types.py        # mapping fidèle des schémas OpenAPI
│   ├── adapters.py             # ParcelleFiche → schemas.py
│   ├── asset_typing.py         # qualification "local commercial" par faisceau d'indices
│   ├── demo_source.py          # source DEMO, même interface que les adapters
│   ├── ingest.py               # orchestration du pipeline, CLI
│   ├── data_cleaning.py
│   ├── owner_resolution.py
│   ├── portfolio.py
│   ├── scoring.py
│   ├── explanations.py         # génération des explications de score
│   ├── enrichment.py
│   └── exports.py
├── ui/
│   ├── dashboard.py
│   ├── properties.py           # TOP 100
│   ├── property_detail.py
│   ├── owners.py
│   └── components.py           # badges de confiance, formatage, carte
├── data/sample/
└── tests/
```

### 5.1 La couche pivot — point critique

`src/schemas.py` : des modèles Pydantic qui décrivent **notre** modèle de domaine, distinct de celui de Pappers. `src/pappers_types.py` est le mapping fidèle des schémas OpenAPI (`ParcelleBase`, `ParcelleFiche`, `Vente`, `Proprietaire`, `Occupant`, `FondsDeCommerce`, `Batiment`, `Dpe`, `Permis`, `Copropriete`, `PersonnePhysique`, `RepresentantPersonneMorale`), et la conversion se fait dans `adapters.py`.

- `demo_source.py` produit des payloads au format `pappers_types.ParcelleFiche`, convertis via `adapters.py`.
- `adapters.py` convertit les payloads Pappers (réels ou démo) en objets `schemas.*`.
- Tout le reste du code (cleaning, resolution, scoring, UI) ne connaît que `schemas.*`.

Résultat : brancher l'API réelle en Phase 3 ne touche qu'au client HTTP. Construire les données DEMO sur un schéma improvisé qui fuit dans le reste du code transformerait la Phase 3 en réécriture — c'est l'erreur à ne pas commettre.

---

## 6. Modèle de données

Tables minimales. Toutes ont `created_at`, `updated_at`, et une colonne `raw_payload` JSONB quand la donnée vient d'une API.

**`properties`** — id, numero_parcelle, adresse_brute, adresse_normalisee, numero, rue, code_postal, code_commune, ville, departement, latitude, longitude, geometrie (JSONB), contenance, type_actif, type_actif_confidence, type_actif_indices (JSONB), usage_batiment, surface_bati, surface_batiment, prix_derniere_mutation, date_derniere_mutation, nature_derniere_mutation, nombre_lots_derniere_mutation, prix_m2, prix_m2_fiable (bool), source, raw_payload

**`owners`** — id, siren, nom_entreprise, nom_normalise, type_proprietaire, categorie_juridique, activite_principale, date_creation, tranche_effectifs, employeur, cessation_activite, nb_parcelles_api, nb_locaux_api, source, raw_payload
Types : `personne_physique`, `sci`, `fonciere`, `institutionnel`, `societe`, `exploitant`, `autre`, `inconnu`
`type_proprietaire` est dérivé de `categorie_juridique` (6540 = SCI, etc.) et de `activite_principale`. La table de correspondance vit dans `config.py`.

**`owner_portfolio_api`** — owner_id, numero_parcelle, adresse, commune, departement, source (`locaux` ou `parcelles`)
Le portefeuille tel que déclaré par l'API, stocké séparément des actifs réellement ingérés dans `properties`.

**`ownership`** — property_id, owner_id, confidence_score, fiabilite_api, source, date_verification
`fiabilite_api` conserve la valeur brute (`haute`/`moyenne`/`faible`) ; `confidence_score` est sa normalisation selon le mapping de `config.py`.

**`occupants`** — property_id, siren, siret, enseigne, nom_entreprise, activite_principale_etablissement, categorie_juridique, date_entree_lieux, date_sortie_lieux, etablissement_ferme, cessation_activite, fiabilite_appartenance_parcelle, raw_payload

**`fonds_de_commerce`** — property_id, activite, prix, date_debut_activite, categorie_vente, origine_fonds, acheteur (JSONB), precedent_proprietaire (JSONB), annonce_bodacc (JSONB), fiabilite_appartenance_parcelle, raw_payload

**`companies`** — siren, siret, nom, forme_juridique, date_creation, code_naf, activite, adresse, dirigeants (JSONB), effectif, source, raw_payload

**`transactions`** — property_id, date, prix, surface, type_mutation, prix_m2, source

**`scores`** — property_id, asset_score, owner_score, sell_signal_score, sourcing_score, score_breakdown (JSONB), score_explanation, config_version, calculated_at

`score_breakdown` stocke le détail critère par critère : c'est ce qui rend le score auditable et alimente la page « Pourquoi cet actif ? ». `config_version` permet de savoir avec quels coefficients un score a été calculé.

---

## 7. Scoring

Système pondéré, transparent, entièrement piloté par `config.py`. Pas de ML.

**Asset Score — 40 points**
Valeur 0–10 (proximité de la cible, sur le prix de dernière mutation, 0 si inconnu) · Surface 0–5 · Prix/m² 0–10 (comparé aux mutations comparables de la même commune et du même type dans la base) · Localisation 0–15 (0 si la qualification d'emplacement n'est pas disponible).

**Owner Score — 30 points**
Taille du portefeuille identifié : 1 actif → 0 · 2–5 → 5 · 6–10 → 10 · >10 → 15.
Typologie : coefficients par type dans `config.py`.
Le portefeuille est celui **identifié dans notre base**, jamais présenté comme le patrimoine total du propriétaire. L'interface doit écrire « 14 actifs identifiés dans la base », pas « détient 14 actifs ».

**Sell Signal Score — 30 points**
Signaux calculables avec les données réellement disponibles :
- ancienneté de la dernière mutation (`Vente.date`) ;
- multiplicité des mutations sur la parcelle (`nombre_ventes`) ;
- cessions récentes ailleurs dans le portefeuille du propriétaire (via `siren_proprietaire`) ;
- mutation de fonds de commerce sur la parcelle (`FondsDeCommerce.annonce_bodacc`, `precedent_proprietaire`) ;
- occupant parti ou établissement fermé (`date_sortie_lieux`, `etablissement_ferme`) ;
- société propriétaire en cessation d'activité (`cessation_activite`) ;
- permis de construire récent sur la parcelle (`statut_permis`, `date_autorisation_permis`) ;
- taille du portefeuille déclaré.

Contrainte de vocabulaire, non négociable et à faire respecter dans `explanations.py` : « signal potentiel », « indice », « à qualifier ». Jamais « le propriétaire veut vendre », « souhaite céder », « est vendeur ». Un test échoue si une explication générée contient un terme de la liste noire.

**Sourcing Score = Asset + Owner + Sell Signal, sur 100.** Les trois composantes sont toujours affichées séparément.

**Explications** générées par templates depuis `score_breakdown`, de façon déterministe. L'IA peut reformuler dans un second temps mais ne doit jamais introduire une information absente de la base — si une reformulation LLM est ajoutée, elle est optionnelle, désactivée par défaut, et le texte déterministe reste consultable.

---

## 8. Mode DEMO

`DATA_SOURCE=demo` ou `DATA_SOURCE=pappers` dans `.env`. Le mode DEMO doit fonctionner sans aucune clé API.

Le jeu DEMO est généré **au format `ParcelleFiche`** de la spec OpenAPI, puis passe par `adapters.py` comme les vraies données. C'est la seule façon de garantir que la Phase 3 se limite à brancher le client HTTP.

Jeu de données fictif, marqué `DEMO DATA — NOT REAL` dans un bandeau permanent de l'interface et dans une colonne de chaque export : 120+ locaux, 4 à 5 villes, une trentaine de propriétaires dont plusieurs multi-actifs, une répartition réaliste des types, et **des trous volontaires** — prix manquants, propriétaires inconnus, coordonnées absentes, doublons d'adresse. Un jeu de démo trop propre ne prouve rien : la gestion des données manquantes est précisément ce que le prototype doit montrer en entretien.

---

## Environnement d'exécution (contrainte locale)

Ce dépôt est développé en WSL Ubuntu. Seul Python 3.14 est disponible (pas de 3.11/3.12), et aucun serveur PostgreSQL n'est installé localement.

- Les colonnes JSONB (`src/models.py`) utilisent `JSONB().with_variant(SQLite JSON, "sqlite")` pour rester compatibles avec des tests unitaires en SQLite en mémoire, tout en restant du vrai JSONB en production Postgres.
- Les tests (`pytest`) tournent donc sans dépendance à un serveur Postgres réel.
- Avant de lancer l'ingestion réelle ou `streamlit run app.py` en pointant vers Postgres, un serveur Postgres doit être provisionné (Docker recommandé) et `DATABASE_URL` renseigné dans `.env`.
