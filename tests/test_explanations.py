import pytest

import config
from src import explanations
from src.schemas import Property, ScoreBreakdownItem, TypeActif


def test_check_no_blacklisted_terms_leve_une_erreur_si_terme_present():
    with pytest.raises(ValueError):
        explanations.check_no_blacklisted_terms("Le propriétaire veut vendre ce local.")


def test_check_no_blacklisted_terms_accepte_le_vocabulaire_prudent():
    explanations.check_no_blacklisted_terms("Signal potentiel identifié, à qualifier.")


@pytest.mark.parametrize("terme", config.EXPLANATION_VOCABULAIRE_INTERDIT)
def test_chaque_terme_de_la_liste_noire_est_detecte(terme):
    with pytest.raises(ValueError):
        explanations.check_no_blacklisted_terms(f"Ce texte contient : {terme}.")


def test_generate_explanation_ne_contient_aucun_terme_interdit():
    property_ = Property(numero_parcelle="TEST0001", type_actif=TypeActif.COMMERCIAL)
    breakdown = [
        ScoreBreakdownItem(critere="Valeur", points=10, points_max=10, detail="Prix dans la cible"),
        ScoreBreakdownItem(critere="mutation_ancienne", points=6, points_max=6, detail="Dernière mutation il y a 9 ans"),
    ]
    texte = explanations.generate_explanation(property_, breakdown, sourcing_score=42.0)
    lowered = texte.lower()
    for terme in config.EXPLANATION_VOCABULAIRE_INTERDIT:
        assert terme not in lowered
    assert "42" in texte
