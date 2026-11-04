#!/usr/bin/env bash
# Reconstruit la base SQLite de démonstration versionnée
# (data/demo/broker_immo_demo.sqlite), lue par l'interface quand aucune
# DATABASE_URL n'est fournie — typiquement sur Streamlit Community Cloud.
#
# C'est bien l'ingestion batch de CLAUDE.md section 3.8 qui produit ce
# fichier, jamais Streamlit. À relancer après toute modification du jeu
# DEMO, du scoring ou du schéma.
#
#   ./scripts/build_demo_db.sh
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
TARGET="data/demo/broker_immo_demo.sqlite"
SCRATCH="$(mktemp -t broker_immo_demo.XXXXXX.sqlite)"
rm -f "$SCRATCH"

export DATABASE_URL="sqlite:///$SCRATCH"
export DATA_SOURCE="demo"

"$PYTHON" -m alembic upgrade head
"$PYTHON" -m src.ingest
"$PYTHON" -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('VACUUM'); c.close()" "$SCRATCH"

mkdir -p "$(dirname "$TARGET")"
mv "$SCRATCH" "$TARGET"
echo "Base DEMO reconstruite : $TARGET"
