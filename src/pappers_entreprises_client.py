"""Client Pappers Entreprises — NON implémenté en V1.

Le schéma `Proprietaire` de Pappers Immobilier (bases=proprietaires) fournit
déjà siren, nom_entreprise, categorie_juridique, activite_principale,
date_creation, tranche_effectifs, employeur, cessation_activite, ainsi que
le portefeuille déclaré (locaux, parcelles). Pappers Entreprises n'apporte
donc rien d'indispensable au scoring de la V1 (CLAUDE.md, section 3.4).

Prévu pour la V2 : comptes annuels et procédures BODACC (mentionnées en
section 7 comme signal de cession de fonds de commerce, actuellement lu via
FondsDeCommerce.annonce_bodacc de Pappers Immobilier — Pappers Entreprises
donnerait un accès plus complet aux procédures BODACC hors fonds de
commerce).
"""
