from src import owner_resolution
from src.schemas import Owner, TypeProprietaire


def test_sci_mappee_depuis_categorie_juridique():
    owner = Owner(siren="123456789", nom_entreprise="SCI DU CENTRE", categorie_juridique="6540")
    assert owner_resolution.resolve_owner_type(owner) == TypeProprietaire.SCI


def test_societe_avec_activite_immobiliere_devient_fonciere():
    owner = Owner(siren="123456789", nom_entreprise="FONCIERE X", categorie_juridique="5785", activite_principale="68.20B")
    assert owner_resolution.resolve_owner_type(owner) == TypeProprietaire.FONCIERE


def test_societe_sans_activite_immobiliere_reste_societe():
    owner = Owner(siren="123456789", nom_entreprise="RETAIL SAS", categorie_juridique="5785", activite_principale="47.19A")
    assert owner_resolution.resolve_owner_type(owner) == TypeProprietaire.SOCIETE


def test_personne_physique_sans_siren_ni_categorie():
    owner = Owner(siren=None, nom_entreprise="DURAND JEAN", categorie_juridique=None)
    assert owner_resolution.resolve_owner_type(owner) == TypeProprietaire.PERSONNE_PHYSIQUE


def test_owner_totalement_vide_est_inconnu():
    owner = Owner()
    assert owner_resolution.resolve_owner_type(owner) == TypeProprietaire.INCONNU


def test_normalize_owner_name():
    assert owner_resolution.normalize_owner_name("  sci   du centre  ") == "SCI DU CENTRE"
    assert owner_resolution.normalize_owner_name(None) is None
