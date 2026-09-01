"""Modèles SQLAlchemy — schéma relationnel (CLAUDE.md, section 6).

Les colonnes JSON utilisent du vrai JSONB en production PostgreSQL, et
basculent automatiquement sur JSON en SQLite (voir `JSON_TYPE` ci-dessous) :
ceci permet de faire tourner les tests sans serveur PostgreSQL, ce qui est
la situation de cet environnement de développement (voir CLAUDE.md,
section "Environnement d'exécution").
"""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSON_TYPE = JSONB().with_variant(SQLITE_JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PropertyModel(TimestampMixin, Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_parcelle: Mapped[str] = mapped_column(String, unique=True, index=True)
    adresse_brute: Mapped[str | None] = mapped_column(String)
    adresse_normalisee: Mapped[str | None] = mapped_column(String)
    numero: Mapped[str | None] = mapped_column(String)
    rue: Mapped[str | None] = mapped_column(String)
    code_postal: Mapped[str | None] = mapped_column(String, index=True)
    code_commune: Mapped[str | None] = mapped_column(String, index=True)
    ville: Mapped[str | None] = mapped_column(String)
    departement: Mapped[str | None] = mapped_column(String, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geometrie: Mapped[dict | None] = mapped_column(JSON_TYPE)
    contenance: Mapped[float | None] = mapped_column(Float)

    type_actif: Mapped[str | None] = mapped_column(String, index=True)
    type_actif_confidence: Mapped[str | None] = mapped_column(String)
    type_actif_indices: Mapped[list | None] = mapped_column(JSON_TYPE)

    usage_batiment: Mapped[str | None] = mapped_column(String)
    nature_batiment: Mapped[str | None] = mapped_column(String)
    surface_bati: Mapped[float | None] = mapped_column(Float)
    surface_batiment: Mapped[float | None] = mapped_column(Float)

    prix_derniere_mutation: Mapped[float | None] = mapped_column(Float)
    date_derniere_mutation: Mapped[datetime.date | None] = mapped_column(Date)
    nature_derniere_mutation: Mapped[str | None] = mapped_column(String)
    type_local_vente: Mapped[str | None] = mapped_column(String)
    nombre_lots_derniere_mutation: Mapped[int | None] = mapped_column(Integer)
    prix_m2: Mapped[float | None] = mapped_column(Float)
    prix_m2_fiable: Mapped[bool] = mapped_column(Boolean, default=False)

    source: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSON_TYPE)

    ownerships: Mapped[list["OwnershipModel"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    occupants: Mapped[list["OccupantModel"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    fonds_de_commerce: Mapped[list["FondsDeCommerceModel"]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    permis: Mapped[list["PermisModel"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    scores: Mapped[list["ScoreModel"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class OwnerModel(TimestampMixin, Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    siren: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    nom_entreprise: Mapped[str | None] = mapped_column(String)
    nom_normalise: Mapped[str | None] = mapped_column(String, index=True)
    type_proprietaire: Mapped[str] = mapped_column(String, default="inconnu", index=True)
    categorie_juridique: Mapped[str | None] = mapped_column(String)
    activite_principale: Mapped[str | None] = mapped_column(String)
    date_creation: Mapped[datetime.date | None] = mapped_column(Date)
    tranche_effectifs: Mapped[str | None] = mapped_column(String)
    employeur: Mapped[bool | None] = mapped_column(Boolean)
    cessation_activite: Mapped[bool | None] = mapped_column(Boolean)
    nb_parcelles_api: Mapped[int] = mapped_column(Integer, default=0)
    nb_locaux_api: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSON_TYPE)

    portefeuille_api: Mapped[list["OwnerPortfolioApiModel"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    ownerships: Mapped[list["OwnershipModel"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class OwnerPortfolioApiModel(TimestampMixin, Base):
    """Portefeuille tel que DÉCLARÉ par l'API (section 3.4). Ne jamais
    additionner avec les actifs de `properties`."""

    __tablename__ = "owner_portfolio_api"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"), index=True)
    numero_parcelle: Mapped[str | None] = mapped_column(String)
    adresse: Mapped[str | None] = mapped_column(String)
    commune: Mapped[str | None] = mapped_column(String)
    departement: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)  # "locaux" ou "parcelles"

    owner: Mapped["OwnerModel"] = relationship(back_populates="portefeuille_api")


class OwnershipModel(TimestampMixin, Base):
    __tablename__ = "ownership"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"), index=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    fiabilite_api: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    date_verification: Mapped[datetime.date | None] = mapped_column(Date)

    property: Mapped["PropertyModel"] = relationship(back_populates="ownerships")
    owner: Mapped["OwnerModel"] = relationship(back_populates="ownerships")


class OccupantModel(TimestampMixin, Base):
    __tablename__ = "occupants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    siren: Mapped[str | None] = mapped_column(String)
    siret: Mapped[str | None] = mapped_column(String)
    enseigne: Mapped[str | None] = mapped_column(String)
    nom_entreprise: Mapped[str | None] = mapped_column(String)
    activite_principale_etablissement: Mapped[str | None] = mapped_column(String)
    categorie_juridique: Mapped[str | None] = mapped_column(String)
    date_entree_lieux: Mapped[datetime.date | None] = mapped_column(Date)
    date_sortie_lieux: Mapped[datetime.date | None] = mapped_column(Date)
    etablissement_ferme: Mapped[bool | None] = mapped_column(Boolean)
    cessation_activite: Mapped[bool | None] = mapped_column(Boolean)
    fiabilite_appartenance_parcelle: Mapped[str | None] = mapped_column(String)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSON_TYPE)

    property: Mapped["PropertyModel"] = relationship(back_populates="occupants")


class FondsDeCommerceModel(TimestampMixin, Base):
    __tablename__ = "fonds_de_commerce"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    activite: Mapped[str | None] = mapped_column(String)
    prix: Mapped[float | None] = mapped_column(Float)
    date_debut_activite: Mapped[datetime.date | None] = mapped_column(Date)
    categorie_vente: Mapped[str | None] = mapped_column(String)
    origine_fonds: Mapped[str | None] = mapped_column(String)
    acheteur: Mapped[dict | None] = mapped_column(JSON_TYPE)
    precedent_proprietaire: Mapped[dict | None] = mapped_column(JSON_TYPE)
    annonce_bodacc: Mapped[dict | None] = mapped_column(JSON_TYPE)
    fiabilite_appartenance_parcelle: Mapped[str | None] = mapped_column(String)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSON_TYPE)

    property: Mapped["PropertyModel"] = relationship(back_populates="fonds_de_commerce")


class CompanyModel(TimestampMixin, Base):
    """Réservée à Pappers Entreprises (V2, non alimentée en V1)."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    siren: Mapped[str | None] = mapped_column(String, index=True)
    siret: Mapped[str | None] = mapped_column(String)
    nom: Mapped[str | None] = mapped_column(String)
    forme_juridique: Mapped[str | None] = mapped_column(String)
    date_creation: Mapped[datetime.date | None] = mapped_column(Date)
    code_naf: Mapped[str | None] = mapped_column(String)
    activite: Mapped[str | None] = mapped_column(String)
    adresse: Mapped[str | None] = mapped_column(String)
    dirigeants: Mapped[dict | None] = mapped_column(JSON_TYPE)
    effectif: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSON_TYPE)


class TransactionModel(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    date: Mapped[datetime.date | None] = mapped_column(Date)
    prix: Mapped[float | None] = mapped_column(Float)
    surface: Mapped[float | None] = mapped_column(Float)
    type_mutation: Mapped[str | None] = mapped_column(String)
    prix_m2: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String)

    property: Mapped["PropertyModel"] = relationship(back_populates="transactions")


class PermisModel(TimestampMixin, Base):
    """Absente de la liste des tables de la section 6 du CLAUDE.md (écart
    du cahier des charges initial), mais nécessaire : `Score.breakdown`
    (signal "permis_recent", section 7) dépend de `Property.permis`, qui
    doit être persisté comme les autres objets liés à une parcelle."""

    __tablename__ = "permis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    numero: Mapped[str | None] = mapped_column(String)
    etat: Mapped[str | None] = mapped_column(String)
    type: Mapped[str | None] = mapped_column(String)
    date_autorisation: Mapped[datetime.date | None] = mapped_column(Date)
    demandeur_siren: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)

    property: Mapped["PropertyModel"] = relationship(back_populates="permis")


class ScoreModel(TimestampMixin, Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    asset_score: Mapped[float] = mapped_column(Float)
    owner_score: Mapped[float] = mapped_column(Float)
    sell_signal_score: Mapped[float] = mapped_column(Float)
    sourcing_score: Mapped[float] = mapped_column(Float, index=True)
    score_breakdown: Mapped[list | None] = mapped_column(JSON_TYPE)
    score_explanation: Mapped[str | None] = mapped_column(Text)
    config_version: Mapped[str] = mapped_column(String)
    calculated_at: Mapped[datetime.datetime] = mapped_column(DateTime)

    property: Mapped["PropertyModel"] = relationship(back_populates="scores")
