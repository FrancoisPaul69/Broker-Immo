#!/usr/bin/env python3
"""Produit le TOP 100 des actifs commerciaux en console, à partir des
données DEMO — critère d'acceptation de la Phase 1 (CLAUDE.md, section 9).

Tourne entièrement en mémoire, sans base de données : ce script sert à
valider le pipeline domaine avant que l'interface (Phase 2) et
l'ingestion/persistance (Phase 3) n'existent.

Usage : python scripts/top100_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.demo_source import generate_demo_parcelles
from src.pipeline import build_properties, score_properties


def main() -> None:
    print(f"=== {config.DEMO_DATA_LABEL} ===\n")

    fiches = generate_demo_parcelles()
    properties = build_properties(fiches, source="demo")
    scores = score_properties(properties)

    proprietes_commerciales = [p for p in properties if p.type_actif.value in ("commercial", "incertain")]
    classement = sorted(proprietes_commerciales, key=lambda p: scores[p.numero_parcelle].sourcing_score, reverse=True)

    print(f"{len(properties)} actifs générés, {len(proprietes_commerciales)} retenus (commercial ou incertain).\n")

    for rang, property_ in enumerate(classement[:100], start=1):
        score = scores[property_.numero_parcelle]
        proprietaire = "propriétaire inconnu"
        if property_.owners:
            owner = max(property_.owners, key=lambda o: o.confidence_score).owner
            proprietaire = owner.nom_entreprise or "propriétaire non nommé"

        print(f"#{rang:>3} | {score.sourcing_score:>5.1f}/100 | {property_.adresse_brute or property_.numero_parcelle}")
        print(
            f"       Actif {score.asset_score:.1f}/{config.ASSET_SCORE_MAX} · "
            f"Propriétaire {score.owner_score:.1f}/{config.OWNER_SCORE_MAX} ({proprietaire}) · "
            f"Signaux {score.sell_signal_score:.1f}/{config.SELL_SIGNAL_SCORE_MAX}"
        )
        print(f"       {score.explanation}")
        print()


if __name__ == "__main__":
    main()
