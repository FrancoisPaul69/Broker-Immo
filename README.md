# Commercial Real Estate Sourcing Engine

Prototype de sourcing d'immobilier commercial. Voir [`CLAUDE.md`](CLAUDE.md)
pour le cahier des charges complet (règles permanentes, spécification de
l'API Pappers Immobilier, architecture, modèle de scoring).

**État actuel : Phase 3 en cours** — pipeline domaine complet (Phase 1),
interface Streamlit multi-pages (Phase 2), client API réel et script
d'ingestion batch (Phase 3, slices 1-2), et **Streamlit qui ne lit plus
que la base** (Phase 3, slice 3 : `src/repository.py`) — plus aucun appel
à `demo_source`/`pipeline` depuis `ui/`. Reste en attente : l'ingestion
réelle par zone (`GET /parcelles`, schéma de réponse non documenté par
Pappers, voir `src/pappers_immo_client.py`).

### Lancer l'interface

Streamlit ne fait plus aucun calcul : la base doit être peuplée au
préalable par une ingestion (mode demo par défaut, aucune clé API requise) :

```bash
cp .env.example .env
# DATABASE_URL par défaut = PostgreSQL ; en local sans serveur Postgres,
# pointer vers un fichier SQLite (voir "Environnement d'exécution" dans CLAUDE.md) :
export DATABASE_URL=sqlite:///broker_immo_demo.db

.venv/bin/python -m alembic upgrade head
.venv/bin/python -m src.ingest                 # ingère tout le jeu DEMO (~130 locaux)
.venv/bin/streamlit run app.py
```

Quatre pages : **Vue d'ensemble** (KPIs et graphiques), **TOP 100**
(classement filtrable), **Fiche actif** (score décomposé, explication,
indices de qualification), **Propriétaires** (portefeuille identifié dans
la base vs portefeuille déclaré par l'API, jamais additionnés). Les
données sont lues depuis la base une seule fois par session
(`st.cache_data` dans `ui/components.py`), jamais recalculées par
Streamlit. Le bandeau "DEMO DATA — NOT REAL" ne s'affiche que si tous les
actifs en base viennent du jeu DEMO.

## Mise en route

Environnement de développement : WSL Ubuntu, Python 3.14 (seule version
disponible), pas de serveur PostgreSQL local — voir la note en fin de
`CLAUDE.md`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # DATA_SOURCE=demo par défaut, aucune clé API requise
```

### Lancer les tests

```bash
.venv/bin/python -m pytest
```

Les tests tournent contre SQLite en mémoire (voir `src/models.py`,
`JSON_TYPE`), pas contre un vrai PostgreSQL.

### Voir le classement TOP 100 (données DEMO)

```bash
.venv/bin/python scripts/top100_demo.py
```

Génère ~130 locaux fictifs, les qualifie, les score et affiche le
classement en console avec les trois sous-scores (Actif / Propriétaire /
Signaux) et l'explication de chacun.

### Base de données PostgreSQL (production / usage au-delà des tests)

En dehors de cet environnement de développement (WSL sans Postgres), un
serveur PostgreSQL doit être provisionné (Docker recommandé) :

```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/broker_immo
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m src.ingest --code-postal 69002
```

### Ingestion avec l'API réelle

```bash
DATA_SOURCE=pappers PAPPERS_IMMO_API_KEY=... .venv/bin/python -m src.ingest --numero-parcelle 69386AB0001
```

Seul `--numero-parcelle` (répétable) est disponible pour l'instant en
mode réel : l'ingestion par zone (`--code-postal`) nécessite `GET
/parcelles`, dont le schéma de réponse n'est pas documenté par Pappers —
voir le TODO dans `src/pappers_immo_client.py` et `PROGRESS.md`.

### Déploiement Streamlit Community Cloud

L'interface ne fait que lire une base, donc un déploiement a besoin d'une
base joignable. Deux cas, dans cet ordre de priorité :

1. **Secret `DATABASE_URL`** renseigné dans l'app (*Settings → Secrets*),
   au format `DATABASE_URL = "postgresql+psycopg://..."`. C'est le mode
   normal : la base distante doit avoir été migrée (`alembic upgrade
   head`) et peuplée (`python -m src.ingest`) depuis un poste de dev.
2. **Repli automatique sur la base DEMO embarquée** —
   `data/demo/broker_immo_demo.sqlite`, versionnée dans le dépôt. Elle
   est utilisée si aucun secret n'est fourni, ou si la base configurée
   est injoignable ; l'interface affiche alors un avertissement explicite.
   L'app démarre donc toujours, même sans secret.

Reconstruire la base DEMO après un changement de jeu de données, de
scoring ou de schéma :

```bash
./scripts/build_demo_db.sh
```

Deux réglages restent à faire dans le dashboard Streamlit Cloud, aucun
fichier du dépôt ne les pilote :

- **Partage** : *Settings → Sharing* doit être sur « Anyone with the link
  can view ». Une app privée renvoie les visiteurs vers l'authentification
  Streamlit, ce qui se manifeste par une page blanche avec un spinner.
- **Version de Python** : choisie dans la boîte de dialogue de
  déploiement (ni `runtime.txt` ni `.python-version` ne sont lus).

## Points ouverts

- Le schéma `Proprietaire` de l'API Pappers Immobilier n'expose pas de
  champ `fiabilite_appartenance_parcelle` (contrairement à `Occupant` et
  `FondsDeCommerce`). Voir le TODO en tête de `src/adapters.py` pour les
  deux lectures possibles.
- Le critère de scoring "Localisation" (0-15 points) n'a aujourd'hui aucune
  source de données réelle : il est figé à 0 (`config.ASSET_LOCALISATION_DISPONIBLE`).
- Le sens du critère "Prix/m²" (décote vs comparables = mieux noté) est une
  hypothèse de sourcing à confirmer, voir le commentaire dans `config.py`.
- `GET /parcelles` (recherche multi-critères) n'a pas de schéma de réponse
  documenté : l'ingestion réelle par zone n'est pas branchée (voir
  `src/pappers_immo_client.py`).
- Le coût de base en jetons d'une requête `/parcelles` n'est pas documenté :
  le compteur de crédits sous-estime la consommation réelle en mode
  `pappers` (voir `config.py`, au-dessus de `CHAMPS_SUPPLEMENTAIRES_COUTS`).

## Nouveau frontend React (migration progressive)

Le design Broker Immo est disponible dans `frontend/`. Il consomme l'API FastAPI de lecture `src/web_api.py`, qui passe exclusivement par `src.repository`. Streamlit reste disponible pendant la migration.

```bash
# Terminal 1
.venv/bin/uvicorn src.web_api:app --reload --port 8000
# Terminal 2
cd frontend && pnpm install && pnpm dev
```

Le frontend est alors disponible sur `http://localhost:5173`. Pour un déploiement séparé, renseigner `VITE_API_BASE_URL` d'après `frontend/.env.example` et autoriser son origine avec `FRONTEND_ORIGINS`.

Endpoints : `GET /api/health` et `GET /api/dataset`.
