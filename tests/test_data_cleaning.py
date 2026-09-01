from datetime import date

from src import data_cleaning
from src.schemas import Property, Transaction


def test_parse_adresse_extrait_numero_et_rue():
    numero, rue = data_cleaning.parse_adresse("16 PLACE SAINT PIERRE 31000 TOULOUSE")
    assert numero == "16"
    assert rue == "PLACE SAINT PIERRE"


def test_parse_adresse_format_inattendu_retourne_none():
    numero, rue = data_cleaning.parse_adresse("adresse mal formée")
    assert (numero, rue) == (None, None)


def test_normalize_adresse_collapse_espaces():
    assert data_cleaning.normalize_adresse("16   place   saint pierre") == "16 Place Saint Pierre"


def test_normalize_adresse_none():
    assert data_cleaning.normalize_adresse(None) is None


def test_clean_property_retient_la_mutation_la_plus_recente():
    property_ = Property(
        numero_parcelle="TEST0001",
        adresse_brute="16 PLACE SAINT PIERRE 31000 TOULOUSE",
        transactions=[
            Transaction(date=date(2015, 1, 1), prix=500_000, surface=100, type_local="local_industriel_commercial_ou_assimile", nombre_lots=1),
            Transaction(date=date(2022, 6, 1), prix=900_000, surface=120, type_local="local_industriel_commercial_ou_assimile", nombre_lots=1),
        ],
    )
    cleaned = data_cleaning.clean_property(property_)
    assert cleaned.prix_derniere_mutation == 900_000
    assert cleaned.date_derniere_mutation == date(2022, 6, 1)
    assert cleaned.surface_bati == 120
    assert cleaned.prix_m2 == 7500.0
    assert cleaned.prix_m2_fiable is True
    assert cleaned.numero == "16"


def test_clean_property_signale_mutation_multi_lots_non_fiable():
    property_ = Property(
        numero_parcelle="TEST0002",
        transactions=[Transaction(date=date(2023, 1, 1), prix=1_000_000, surface=200, nombre_lots=3)],
    )
    cleaned = data_cleaning.clean_property(property_)
    assert cleaned.prix_m2 == 5000.0  # calculé...
    assert cleaned.prix_m2_fiable is False  # ...mais signalé non fiable (section 3.6)


def test_clean_property_sans_mutation_ne_devine_rien():
    property_ = Property(numero_parcelle="TEST0003")
    cleaned = data_cleaning.clean_property(property_)
    assert cleaned.prix_derniere_mutation is None
    assert cleaned.prix_m2 is None
