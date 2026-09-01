from src import asset_typing
from src.schemas import ConfianceTyping, FondsDeCommerce, Occupant, Property, TypeActif


def _property(**overrides) -> Property:
    base = {"numero_parcelle": "TEST0001"}
    base.update(overrides)
    return Property(**base)


def test_local_residentiel_est_exclu_avec_haute_confiance():
    property_ = _property(type_local_vente="maison")
    result = asset_typing.qualify(property_)
    assert result.type_actif == TypeActif.AUTRE
    assert result.confidence == ConfianceTyping.HAUTE


def test_faisceau_indices_fort_donne_commercial_haute_confiance():
    property_ = _property(
        type_local_vente="local_industriel_commercial_ou_assimile",
        usage_batiment="commercial_et_services",
        nature_batiment="industriel_agricole_ou_commercial",
        surface_bati=80,
        fonds_de_commerce=[FondsDeCommerce(activite="Boulangerie")],
        occupants=[Occupant(activite_principale_etablissement="47.11D", enseigne="Ma Boutique")],
    )
    result = asset_typing.qualify(property_)
    assert result.type_actif == TypeActif.COMMERCIAL
    assert result.confidence == ConfianceTyping.HAUTE
    assert len(result.indices) >= 5


def test_faisceau_indices_negatif_donne_industriel():
    property_ = _property(
        type_local_vente="local_industriel_commercial_ou_assimile",
        usage_batiment="industriel",
        nature_batiment="silo",
        surface_bati=5000,
        occupants=[Occupant(activite_principale_etablissement="52.10B")],
    )
    result = asset_typing.qualify(property_)
    assert result.type_actif == TypeActif.INDUSTRIEL_OU_ENTREPOT
    assert result.confidence == ConfianceTyping.HAUTE


def test_absence_indices_donne_incertain_faible():
    property_ = _property(type_local_vente="local_industriel_commercial_ou_assimile")
    result = asset_typing.qualify(property_)
    assert result.type_actif == TypeActif.INCERTAIN
    assert result.confidence == ConfianceTyping.FAIBLE


def test_naf_section_mapping():
    assert asset_typing.naf_section("47.11D") == "G"
    assert asset_typing.naf_section("56.10A") == "I"
    assert asset_typing.naf_section("52.10B") == "H"
    assert asset_typing.naf_section("10.71A") == "C"
    assert asset_typing.naf_section(None) is None
