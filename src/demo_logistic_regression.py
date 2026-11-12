"""Régression logistique illustrative, réservée au jeu de données DEMO.

Les résultats de prospection sont simulés à partir des caractéristiques des
actifs : les probabilités produites ne sont ni des prédictions métier ni des
résultats validés sur des données réelles.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import config
from src.schemas import Property, TypeActif

_FEATURE_NAMES = tuple(config.DEMO_LOGISTIC_LABEL_WEIGHTS)


@dataclass(frozen=True)
class DemoLogisticPrediction:
    """Probabilité out-of-fold et étiquette synthétique d'un actif DEMO."""

    probability: float
    synthetic_qualified_label: bool


@dataclass(frozen=True)
class DemoLogisticResult:
    """Prédictions de démonstration et nombre de plis utilisés."""

    predictions: dict[str, DemoLogisticPrediction]
    cross_validation_folds: int


def _features(property_: Property) -> dict[str, float]:
    price = property_.prix_derniere_mutation
    surface = property_.surface_bati
    return {
        "commercial": float(property_.type_actif == TypeActif.COMMERCIAL),
        "incertain": float(property_.type_actif == TypeActif.INCERTAIN),
        "surface_cible": float(
            surface is not None
            and config.ASSET_SURFACE_CIBLE_MIN <= surface <= config.ASSET_SURFACE_CIBLE_MAX
        ),
        "prix_cible": float(
            price is not None
            and config.ASSET_VALEUR_CIBLE_MIN <= price <= config.ASSET_VALEUR_CIBLE_MAX
        ),
        "proprietaire_identifie": float(bool(property_.owners)),
        "occupant_parti": float(
            any(occupant.date_sortie_lieux is not None or occupant.etablissement_ferme for occupant in property_.occupants)
        ),
        "mutations_multiples": float(len(property_.transactions) >= 2),
    }


def train_demo_logistic_regression(properties: list[Property]) -> DemoLogisticResult | None:
    """Entraîne et évalue par validation croisée le modèle DEMO.

    Renvoie ``None`` pour un jeu réel ou vide. Une erreur explicite est levée
    si un jeu DEMO est trop petit pour une validation croisée stratifiée.
    """
    if not properties or not all(property_.source == "demo" for property_ in properties):
        return None

    rows = [_features(property_) for property_ in properties]
    matrix = np.asarray([[row[name] for name in _FEATURE_NAMES] for row in rows], dtype=float)
    weights = config.DEMO_LOGISTIC_LABEL_WEIGHTS
    rng = random.Random(config.DEMO_LOGISTIC_SEED)
    labels: list[int] = []

    for row in rows:
        logit = config.DEMO_LOGISTIC_LABEL_INTERCEPT + sum(
            row[name] * weights[name] for name in _FEATURE_NAMES
        )
        probability = 1 / (1 + math.exp(-logit))
        labels.append(int(rng.random() < probability))

    class_counts = np.bincount(labels, minlength=2)
    folds = min(config.DEMO_LOGISTIC_MAX_CV_SPLITS, int(class_counts.min()))
    if folds < 2:
        raise ValueError(
            "La régression logistique DEMO nécessite au moins deux exemples "
            "de chaque classe synthétique."
        )

    estimator = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=config.DEMO_LOGISTIC_MAX_ITER, random_state=config.DEMO_LOGISTIC_SEED),
    )
    cross_validation = StratifiedKFold(
        n_splits=folds, shuffle=True, random_state=config.DEMO_LOGISTIC_SEED
    )
    probabilities = cross_val_predict(
        estimator, matrix, np.asarray(labels), cv=cross_validation, method="predict_proba"
    )[:, 1]

    predictions = {
        property_.numero_parcelle: DemoLogisticPrediction(
            probability=float(probability),
            synthetic_qualified_label=bool(label),
        )
        for property_, probability, label in zip(properties, probabilities, labels, strict=True)
    }
    return DemoLogisticResult(predictions=predictions, cross_validation_folds=folds)
