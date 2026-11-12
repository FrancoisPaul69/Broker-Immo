from src.demo_logistic_regression import train_demo_logistic_regression
from src.demo_source import generate_demo_parcelles
from src.pipeline import build_properties


def test_modele_logistique_demo_produit_des_probabilites_reproductibles():
    properties = build_properties(generate_demo_parcelles(), source="demo")

    first = train_demo_logistic_regression(properties)
    second = train_demo_logistic_regression(properties)

    assert first is not None
    assert second is not None
    assert first.cross_validation_folds >= 2
    assert first.predictions == second.predictions
    assert len(first.predictions) == len(properties)
    assert all(0 <= item.probability <= 1 for item in first.predictions.values())
    assert {item.synthetic_qualified_label for item in first.predictions.values()} == {False, True}


def test_modele_logistique_ne_s_entraine_pas_sur_une_source_non_demo():
    properties = build_properties(generate_demo_parcelles(), source="pappers")

    assert train_demo_logistic_regression(properties) is None
