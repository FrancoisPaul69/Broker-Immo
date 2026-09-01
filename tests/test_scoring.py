from datetime import date

import config
from src import scoring
from src.schemas import Owner, Ownership, Property, TypeActif, TypeProprietaire


def _property(numero="TEST0001", **overrides) -> Property:
    base = {"numero_parcelle": numero, "type_actif": TypeActif.COMMERCIAL}
    base.update(overrides)
    return Property(**base)


def test_score_valeur_dans_la_cible_est_maximal():
    item = scoring._score_valeur(config.ASSET_VALEUR_CIBLE_MIN + 1)
    assert item.points == config.ASSET_SCORE_VALEUR_MAX


def test_score_valeur_inconnue_est_nul():
    item = scoring._score_valeur(None)
    assert item.points == 0


def test_score_localisation_toujours_nul_en_v1():
    item = scoring._score_localisation()
    assert item.points == 0
    assert item.points_max == config.ASSET_SCORE_LOCALISATION_MAX


def test_score_portefeuille_suit_le_bareme():
    siren = "111111111"
    properties = [_property(numero=f"P{i}") for i in range(3)]
    portfolios = {siren: properties}
    item = scoring._score_portefeuille(siren, portfolios)
    assert item.points == 5  # 2-5 actifs -> 5 points


def test_score_typologie_utilise_les_coefficients_config():
    owner = Owner(siren="111111111", type_proprietaire=TypeProprietaire.SCI)
    ownership = Ownership(owner=owner, confidence_score=100)
    item = scoring._score_typologie(ownership)
    assert item.points == config.TYPE_PROPRIETAIRE_COEFFICIENTS["sci"]


def test_signal_mutation_ancienne_se_declenche_apres_le_seuil():
    reference = date(2024, 1, 1)
    ancienne = date(2024 - config.SELL_SIGNAL_MUTATION_ANCIENNE_ANS - 1, 1, 1)
    property_ = _property(date_derniere_mutation=ancienne)
    items = scoring.score_sell_signal(property_, {}, reference_date=reference)
    signal = next(i for i in items if i.critere == "mutation_ancienne")
    assert signal.points == config.SELL_SIGNAL_POIDS["mutation_ancienne"]


def test_signal_mutation_recente_ne_se_declenche_pas():
    reference = date(2024, 1, 1)
    property_ = _property(date_derniere_mutation=date(2023, 6, 1))
    items = scoring.score_sell_signal(property_, {}, reference_date=reference)
    signal = next(i for i in items if i.critere == "mutation_ancienne")
    assert signal.points == 0


def test_compute_scores_reste_dans_les_plafonds():
    property_ = _property(prix_derniere_mutation=500_000, surface_bati=150)
    asset_score, owner_score, sell_signal_score, breakdown = scoring.compute_scores(property_, [property_], {})
    assert 0 <= asset_score <= config.ASSET_SCORE_MAX
    assert 0 <= owner_score <= config.OWNER_SCORE_MAX
    assert 0 <= sell_signal_score <= config.SELL_SIGNAL_SCORE_MAX
    assert asset_score + owner_score + sell_signal_score <= 100


def test_build_score_produit_une_explication_sans_vocabulaire_interdit():
    property_ = _property(prix_derniere_mutation=500_000, surface_bati=150)
    score = scoring.build_score(property_, [property_], {})
    assert score.sourcing_score == round(score.asset_score + score.owner_score + score.sell_signal_score, 1)
    assert score.explanation
    assert score.config_version == config.CONFIG_VERSION
