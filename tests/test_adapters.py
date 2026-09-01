from src import adapters
from src import pappers_types as pt


def test_parcelle_fiche_to_property_conversion_structurelle():
    fiche = pt.ParcelleFiche(
        numero="69386AB0001",
        adresse="12 Rue de la République 69003 Lyon",
        code_commune="69386",
        commune="Lyon",
        codes_postaux=["69003"],
        contenance=500,
        proprietaires=[pt.Proprietaire(siren="123456789", nom_entreprise="SCI TEST", categorie_juridique="6540")],
        occupants=[pt.Occupant(siren="987654321", enseigne="Ma Boutique", fiabilite_appartenance_parcelle="haute")],
    )
    property_ = adapters.parcelle_fiche_to_property(fiche, source="demo")

    assert property_.numero_parcelle == "69386AB0001"
    assert property_.source == "demo"
    assert len(property_.owners) == 1
    assert property_.owners[0].owner.siren == "123456789"
    # TODO connu (voir docstring adapters.py) : pas de fiabilite_appartenance_parcelle
    # sur Proprietaire dans la spec API -> confidence_score reste à 0.
    assert property_.owners[0].confidence_score == 0
    assert len(property_.occupants) == 1
    assert property_.occupants[0].confidence_score == 100  # "haute" -> 100


def test_bounding_box_centroid_absent_sans_donnee():
    fiche = pt.ParcelleFiche(numero="69386AB0002")
    property_ = adapters.parcelle_fiche_to_property(fiche, source="demo")
    assert property_.latitude is None
    assert property_.longitude is None
