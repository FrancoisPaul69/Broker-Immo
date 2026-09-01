"""Test d'intégration correspondant au critère d'acceptation de la Phase 1
(CLAUDE.md, section 9) : le pipeline complet doit produire, à partir des
données DEMO, un classement avec les trois sous-scores et une explication —
sans base de données ni clé API.
"""

import config
from src.demo_source import generate_demo_parcelles
from src.pipeline import build_properties, score_properties
from src.schemas import TypeActif


def test_pipeline_demo_bout_en_bout():
    fiches = generate_demo_parcelles()
    assert len(fiches) == config.DEMO_NB_LOCAUX

    properties = build_properties(fiches, source="demo")
    assert len(properties) == config.DEMO_NB_LOCAUX
    assert all(p.source == "demo" for p in properties)

    # Répartition réaliste des types (section 8) : les quatre issues de la
    # qualification doivent être représentées dans le jeu DEMO.
    types_presents = {p.type_actif for p in properties}
    assert types_presents == {TypeActif.COMMERCIAL, TypeActif.INDUSTRIEL_OU_ENTREPOT, TypeActif.INCERTAIN, TypeActif.AUTRE}

    # Trous volontaires (section 8).
    assert any(p.prix_derniere_mutation is None for p in properties)
    assert any(not p.owners for p in properties)
    assert any(p.latitude is None for p in properties)

    scores = score_properties(properties)
    assert len(scores) == len(properties)

    proprietes_commerciales = [p for p in properties if p.type_actif in (TypeActif.COMMERCIAL, TypeActif.INCERTAIN)]
    classement = sorted(proprietes_commerciales, key=lambda p: scores[p.numero_parcelle].sourcing_score, reverse=True)
    top_100 = classement[:100]

    assert len(top_100) > 0
    for property_ in top_100:
        score = scores[property_.numero_parcelle]
        assert 0 <= score.sourcing_score <= 100
        assert score.explanation
        for terme in config.EXPLANATION_VOCABULAIRE_INTERDIT:
            assert terme not in score.explanation.lower()

    # Le classement est bien trié par score décroissant.
    sourcing_scores = [scores[p.numero_parcelle].sourcing_score for p in top_100]
    assert sourcing_scores == sorted(sourcing_scores, reverse=True)


def test_generation_est_deterministe():
    """Le seed fixe (config.DEMO_RANDOM_SEED) garantit un jeu reproductible,
    utile pour des captures d'écran ou une démo en entretien stables."""
    fiches_1 = generate_demo_parcelles()
    fiches_2 = generate_demo_parcelles()
    assert [f.numero for f in fiches_1] == [f.numero for f in fiches_2]
    assert [f.adresse for f in fiches_1] == [f.adresse for f in fiches_2]
