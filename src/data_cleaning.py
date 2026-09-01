"""Nettoyage et calcul des champs dérivés (CLAUDE.md, section 3.6 et règle 5).

Ce module ne touche jamais à `raw_payload` ni aux champs bruts : il calcule
des valeurs normalisées à côté (adresse_normalisee, prix_m2...). Il
s'applique après `adapters.py` et avant `asset_typing.py` (qui a besoin de
`type_local_vente`, calculé ici à partir de la dernière mutation).
"""

from __future__ import annotations

import re

from src.schemas import Property, Transaction

_ADRESSE_RE = re.compile(r"^(?P<numero>\d+\s?[a-zA-Z]?)\s+(?P<rue>.+?)\s+\d{5}\s+.+$")


def normalize_adresse(adresse_brute: str | None) -> str | None:
    """Normalisation légère d'affichage : espaces multiples réduits, casse
    titre. Ne corrige ni ne devine l'adresse (règle 2)."""
    if not adresse_brute:
        return None
    collapsed = re.sub(r"\s+", " ", adresse_brute).strip()
    return collapsed.title()


def parse_adresse(adresse_brute: str | None) -> tuple[str | None, str | None]:
    """Extrait (numero, rue) d'une adresse au format DVF/cadastre
    "16 PLACE SAINT PIERRE 31000 TOULOUSE". Retourne (None, None) si le
    format ne correspond pas au motif attendu, plutôt que de deviner."""
    if not adresse_brute:
        return None, None
    match = _ADRESSE_RE.match(adresse_brute.strip())
    if not match:
        return None, None
    return match.group("numero").strip(), match.group("rue").strip()


def _clean_transaction(transaction: Transaction) -> Transaction:
    """Calcule prix_m2 et le signale comme non fiable sur une mutation
    multi-lots (section 3.6) plutôt que de l'omettre silencieusement."""
    prix_m2 = None
    if transaction.prix is not None and transaction.surface:
        prix_m2 = round(transaction.prix / transaction.surface, 2)

    multi_lot = transaction.nombre_lots is not None and transaction.nombre_lots > 1
    prix_m2_fiable = prix_m2 is not None and not multi_lot

    return transaction.model_copy(update={"prix_m2": prix_m2, "prix_m2_fiable": prix_m2_fiable})


def _derniere_mutation(transactions: list[Transaction]) -> Transaction | None:
    datees = [t for t in transactions if t.date is not None]
    if not datees:
        return None
    return max(datees, key=lambda t: t.date)


def clean_property(property_: Property) -> Property:
    """Retourne une copie de `property_` avec les champs dérivés remplis."""
    transactions_nettoyees = [_clean_transaction(t) for t in property_.transactions]
    derniere = _derniere_mutation(transactions_nettoyees)
    numero, rue = parse_adresse(property_.adresse_brute)

    updates: dict = {
        "transactions": transactions_nettoyees,
        "adresse_normalisee": normalize_adresse(property_.adresse_brute),
        "numero": numero,
        "rue": rue,
    }

    if derniere is not None:
        updates.update(
            {
                "prix_derniere_mutation": derniere.prix,
                "date_derniere_mutation": derniere.date,
                "nature_derniere_mutation": derniere.type_mutation,
                "type_local_vente": derniere.type_local,
                "nombre_lots_derniere_mutation": derniere.nombre_lots,
                "prix_m2": derniere.prix_m2,
                "prix_m2_fiable": derniere.prix_m2_fiable,
                "surface_bati": derniere.surface,
            }
        )

    return property_.model_copy(update=updates)
