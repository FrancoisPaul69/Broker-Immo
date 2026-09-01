# Journal d'avancement

Récapitulatif phase par phase, tenu à jour au fil du développement (voir
`CLAUDE.md` section 2, règle 8 : construction progressive, une phase à la
fois, validée avant la suivante).

## Phase 1 — Fondations (terminée)

Pipeline domaine complet, entièrement en mémoire, sans base de données ni
API réelle.

- `src/schemas.py` — couche pivot Pydantic (modèle métier), indépendante
  du format Pappers.
- `src/pappers_types.py` — mapping fidèle des schémas OpenAPI Pappers Immobilier.
- `src/adapters.py` — conversion `ParcelleFiche` (Pappers) → `Property` (métier).
- `src/demo_source.py` — jeu de données DEMO généré au format `ParcelleFiche`,
  avec trous volontaires (prix manquants, propriétaires inconnus, etc.).
- `src/asset_typing.py` — qualification "local commercial" par faisceau
  d'indices (section 3.3 du cahier des charges).
- `src/data_cleaning.py`, `src/owner_resolution.py`, `src/portfolio.py` —
  nettoyage, résolution propriétaire, regroupement de portefeuille (base
  uniquement, jamais le portefeuille déclaré par l'API).
- `src/scoring.py` — Asset Score (40) / Owner Score (30) / Sell Signal
  Score (30), entièrement piloté par `config.py`.
- `src/explanations.py` — génération déterministe des explications de
  score, vocabulaire prudent imposé (pas de "veut vendre").
- `src/pipeline.py` — orchestration commune (utilisée par la démo et,
  plus tard, par l'ingestion).
- Tests unitaires sur chaque module (`tests/`).

**Points ouverts identifiés** (voir README, "Points ouverts") :
absence de `fiabilite_appartenance_parcelle` sur `Proprietaire`, critère
"Localisation" sans source de données en V1, sens du critère "Prix/m²" à
confirmer avec le métier.

## Phase 2 — Interface (terminée)

Interface Streamlit multi-pages, consommant le pipeline Phase 1
directement en mémoire (pas encore de base de données — voir Phase 3).

- `app.py` — routeur mince (`st.navigation`), bandeau "DEMO DATA — NOT
  REAL" permanent sur toutes les pages.
- `ui/dashboard.py` — vue d'ensemble : KPIs, répartition par type d'actif,
  confiance de qualification, distribution des scores (Plotly).
- `ui/properties.py` — TOP 100 filtrable (type d'actif, confiance, ville).
- `ui/property_detail.py` — fiche détail avec **le détail du score
  critère par critère** (`score.breakdown`), pas seulement les trois
  sous-totaux : c'est ce qui rend le score auditable en entretien.
- `ui/owners.py` — page Propriétaires, distinguant explicitement le
  portefeuille identifié dans la base et le portefeuille déclaré par
  l'API (jamais additionnés, règle section 3.4/7).
- `ui/components.py` — chargement du jeu DEMO mis en cache
  (`st.cache_data`), badges de confiance.

**Bug trouvé et corrigé en cours de route** : les quatre fonctions de page
s'appelaient toutes `render`, ce que Streamlit utilisait pour déduire le
chemin d'URL — collision qui aurait fait planter la navigation. Détecté
via `streamlit.testing.v1.AppTest` (un simple `curl` ne le voyait pas,
Streamlit sert la même page HTML pour toutes les routes). Corrigé avec des
`url_path` explicites.

**Vérifications effectuées** : suite de tests complète (48/48), démarrage
réel de l'app, exécution de chaque page via `AppTest` sans exception.

## Phase 3 — API réelle et persistance (en cours)

### Slice 1 — Client HTTP Pappers Immobilier (terminée)

- `src/pappers_types.py` — ajout de `ParcelleSearchParams` : les 76
  paramètres de `GET /parcelles` (extraits programmatiquement de
  `api_1.0.0.yaml` pour éviter tout oubli), avec `to_query_params()`
  (dates en `AAAA-MM-JJ`, listes en chaîne séparée par virgules).
- `src/pappers_immo_client.py` — `PappersImmoClient` : auth `api-key`,
  retry avec backoff exponentiel (erreurs transitoires uniquement — 400/
  401/404 ne sont jamais retentées), compteur de jetons
  (`credits_used`), garde-fou `MAX_CREDITS_PER_RUN` vérifié **avant**
  l'envoi de la requête (`CreditBudgetExceeded`).
  - `get_parcelle_fiche()` (`GET /parcelles/{numero_parcelle}`) —
    pleinement implémenté, schéma de réponse entièrement documenté.
  - `search_parcelles()` (`GET /parcelles`) — construit et envoie la
    requête (paramètres documentés), mais **retourne le JSON brut**,
    volontairement non parsé en `list[ParcelleFiche]`.
- Tests avec une fausse session HTTP (`tests/test_pappers_immo_client.py`,
  `tests/test_pappers_types.py`), aucun appel réseau réel.

**Écart de documentation trouvé et signalé à l'utilisateur avant de
coder** (règle 1, CLAUDE.md — ne pas deviner) :

1. `api_1.0.0.yaml` documente la réponse de `GET /parcelles` (recherche,
   liste) comme un simple `$ref: ParcelleFiche` (l'objet d'**une seule**
   parcelle) — aucun schéma pour un objet liste avec `curseurSuivant` /
   `total`, alors que ces champs sont mentionnés en texte libre (spec et
   CLAUDE.md section 3.8). Décision validée : ne pas deviner le format ;
   `search_parcelles()` retourne le JSON brut en attendant soit un
   exemple de réponse réelle, soit une documentation Pappers à jour.
2. Le coût de base en jetons d'une requête `/parcelles` (indépendant des
   champs supplémentaires) n'est documenté nulle part. Décision validée :
   `estimate_cost()` / `credits_used` ne comptabilisent que les surcoûts
   documentés de `config.CHAMPS_SUPPLEMENTAIRES_COUTS` — **sous-estiment
   donc la consommation réelle**. Voir le TODO au-dessus de
   `CHAMPS_SUPPLEMENTAIRES_COUTS` dans `config.py`.

Tant que le point 1 n'est pas résolu, l'ingestion par balayage de zone
(`--code-postal ...`) ne peut pas être branchée sur `search_parcelles()`
sans deviner un format de réponse. À rediscuter à la prochaine slice
(`src/ingest.py`) : soit se limiter à une liste explicite de
`numero_parcelle` en V1 réelle, soit obtenir un exemple de réponse avant
d'aller plus loin.

### Slice 2 — Script d'ingestion (terminée)

- `src/ingest.py` — orchestration batch complète : collecte des fiches →
  pipeline (`build_properties`, `score_properties`) → persistance
  SQLAlchemy. CLI : `python -m src.ingest --code-postal 69002
  [--dry-run]` (mode demo) ou `--numero-parcelle X --numero-parcelle Y`
  (mode pappers, seul mode d'ingestion réelle disponible pour l'instant —
  voir le blocage de la Slice 1 sur `search_parcelles`).
- Cache TTL respecté : une parcelle déjà en base et fraîche
  (`config.CACHE_TTL_DAYS`) est reconstruite depuis son `raw_payload`
  plutôt que réinterrogée (`repartir_cache`). `--dry-run` estime le coût
  en jetons des seules parcelles qui seraient réellement interrogées.
- Persistance idempotente : `properties`/`owners` sont mis à jour en
  place (par `numero_parcelle`/`siren`), pas dupliqués à chaque
  réingestion. `scores` s'accumule volontairement (historique des
  calculs, un run = une nouvelle ligne).
- Tests avec SQLite en mémoire (`tests/test_ingest.py`) + vérification
  manuelle bout en bout sur un fichier SQLite jetable (migration Alembic,
  CLI réel, inspection des lignes, triple ré-ingestion).

**Bug trouvé et corrigé en cours de route** (découvert en testant
réellement l'idempotence, pas en relisant le code) : les propriétaires
sans SIREN (personnes physiques du jeu DEMO — 5 profils dans
`demo_source.py`) créaient une nouvelle ligne `owners` à chaque
réingestion, faute d'identifiant pour les retrouver. Corrigé en
réutilisant le propriétaire sans SIREN déjà rattaché à **cette même
parcelle** lors du run précédent (`_proprietaires_sans_siren_deja_rattaches`),
sans jamais regrouper deux propriétaires sans SIREN de parcelles
différentes par similarité de nom — même principe que
`portfolio.owners_by_siren` (règle 2/3, CLAUDE.md : pas de
regroupement sans identifiant fiable).

### Slice 3 — Bascule de l'interface sur la base (terminée)

- `src/repository.py` — reconstruction de `schemas.Property`/`Score`
  depuis les lignes SQLAlchemy (mapping inverse de
  `ingest.persister_property`), avec chargement anticipé des relations
  (`selectinload`) pour éviter le N+1. Retourne le score le **plus
  récent** par actif (`scores` accumule un historique).
- `ui/components.py` — `load_demo_dataset()` devient `load_dataset()` :
  lit la base via `repository.load_properties()`, ne génère plus rien en
  mémoire. Ajout de `is_demo_dataset()` pour piloter le bandeau "DEMO
  DATA — NOT REAL" (affiché seulement si TOUS les actifs en base ont
  `source="demo"` — jamais sur des données réellement issues de l'API).
- Les 4 pages (`ui/dashboard.py`, `properties.py`, `property_detail.py`,
  `owners.py`) affichent un message actionnable et distinct si la base
  est vide ("lancez une ingestion") vs si elle contient des actifs mais
  aucun commercial/incertain.
- Tests avec SQLite en mémoire (`tests/test_repository.py`) + vérification
  manuelle : ingestion réelle de 130 actifs DEMO dans un fichier SQLite,
  puis chaque page testée via `AppTest` contre cette vraie base (succès),
  et re-testée contre une base fraîchement migrée mais vide (messages
  corrects, aucune exception).

**Deux écarts de persistance trouvés et corrigés en cours de route**
(par un contrôle systématique champs `schemas.py` vs colonnes
SQLAlchemy, pas en relisant le code à l'œil) :

1. `Property.nature_batiment` — utilisé par `asset_typing.py` (indice de
   qualification n°3, section 3.3 du CLAUDE.md) mais absent de
   `PropertyModel`. La table `properties` de la section 6 du CLAUDE.md
   ne le liste pas non plus : écart préexistant du cahier des charges,
   pas introduit par cette tranche.
2. `Occupant.confidence_score`/`source` et `FondsDeCommerce.confidence_score`/`source`
   — présents dans `schemas.py`, jamais persistés.
3. Table `permis` totalement absente de la section 6 du CLAUDE.md alors
   que `Score` (section 7, signal "permis_recent") en dépend — ajoutée
   dans la Slice 2, mais son omission n'aurait été visible qu'en Slice 3
   (lecture base), d'où sa mention ici aussi.

Trois migrations Alembic ajoutées pour ces corrections
(`7829421333dd`, `e45397ac4b71`, en plus de la table `permis` de la
Slice 2) — schéma vérifié sans dérive (`alembic check`).

### Prochaine étape possible

- Provisionnement PostgreSQL (Docker) pour un usage réel au-delà des
  tests et de SQLite local.
- Débloquer l'ingestion réelle par zone (`GET /parcelles`) dès qu'un
  exemple de réponse ou une documentation à jour sera disponible (voir
  Slice 1).
