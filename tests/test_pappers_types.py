import datetime

from src.pappers_types import ParcelleSearchParams


def test_to_query_params_omet_les_champs_absents():
    params = ParcelleSearchParams(code_postal="69002")
    assert params.to_query_params() == {"code_postal": "69002"}


def test_to_query_params_joint_les_listes_par_des_virgules():
    params = ParcelleSearchParams(bases=["proprietaires", "ventes"], champs_supplementaires=["adresse"])
    query = params.to_query_params()
    assert query["bases"] == "proprietaires,ventes"
    assert query["champs_supplementaires"] == "adresse"


def test_to_query_params_formate_les_dates_en_aaaa_mm_jj():
    params = ParcelleSearchParams(date_vente_min=datetime.date(2020, 1, 15))
    assert params.to_query_params()["date_vente_min"] == "2020-01-15"
