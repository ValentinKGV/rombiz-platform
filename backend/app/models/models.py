"""
SQLAlchemy ORM Models â€” Complete schema for the RomBiz platform.
All monetary values use Numeric (NEVER float â€” hard constraint #1 / #15).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.compat_types import CompatUUID as UUID, CompatJSON as JSONB, CompatARRAY as ARRAY, CompatINET as INET, CompatBigInt


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ORGANIZATIONS (Multi-tenancy root entity)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cui: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="FREE")
    subscription_status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    monthly_api_calls: Mapped[int] = mapped_column(Integer, default=0)
    api_calls_limit: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    portfolios = relationship("MonitoredPortfolio", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="organization", cascade="all, delete-orphan")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# USERS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("organizations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(
        String(20), default="viewer",
        info={"check": "role IN ('admin','analyst','viewer')"}
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    api_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    credits_left: Mapped[int] = mapped_column(Integer, default=0)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    alert_preferences: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="users")

    __table_args__ = (
        Index("idx_users_org", "org_id"),
        Index("idx_users_email", "email"),
        CheckConstraint("role IN ('admin','analyst','viewer')", name="ck_users_role"),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# API KEYS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    key_prefix: Mapped[Optional[str]] = mapped_column(String(8))
    permissions: Mapped[dict] = mapped_column(JSONB, default=["read"])
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60)
    total_calls: Mapped[int] = mapped_column(BigInteger, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="api_keys")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COMPANIES (Core entity)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    cui: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    j_nr: Mapped[Optional[str]] = mapped_column(String(20))
    denumire: Mapped[str] = mapped_column(String(500), nullable=False)
    forma_juridica: Mapped[Optional[str]] = mapped_column(String(10))
    stare: Mapped[str] = mapped_column(String(20), default="ACTIVA")
    data_infiintare: Mapped[Optional[date]] = mapped_column(Date)
    data_radiere: Mapped[Optional[date]] = mapped_column(Date)
    caen_principal: Mapped[Optional[str]] = mapped_column(String(4))
    capital_social: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    adresa_completa: Mapped[Optional[str]] = mapped_column(Text)
    judet: Mapped[Optional[str]] = mapped_column(String(50))
    localitate: Mapped[Optional[str]] = mapped_column(String(100))
    cod_postal: Mapped[Optional[str]] = mapped_column(String(10))
    lat: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    lng: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))

    # Contact
    telefon: Mapped[Optional[str]] = mapped_column(String(30))
    fax: Mapped[Optional[str]] = mapped_column(String(30))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    email: Mapped[Optional[str]] = mapped_column(String(254))

    # Status fiscal ANAF
    platitor_tva: Mapped[bool] = mapped_column(Boolean, default=False)
    tva_la_incasare: Mapped[bool] = mapped_column(Boolean, default=False)
    split_tva: Mapped[bool] = mapped_column(Boolean, default=False)
    inactiv_fiscal: Mapped[bool] = mapped_column(Boolean, default=False)
    status_ro_efactura: Mapped[bool] = mapped_column(Boolean, default=False)
    tva_perioade: Mapped[Optional[list]] = mapped_column(JSONB)

    # Denormalized flags for fast filtering
    has_insolvency: Mapped[bool] = mapped_column(Boolean, default=False)
    has_litigation: Mapped[bool] = mapped_column(Boolean, default=False)
    has_debts: Mapped[bool] = mapped_column(Boolean, default=False)
    has_seap_contracts: Mapped[bool] = mapped_column(Boolean, default=False)
    has_eu_projects: Mapped[bool] = mapped_column(Boolean, default=False)
    has_trademarks: Mapped[bool] = mapped_column(Boolean, default=False)

    data_quality_score: Mapped[int] = mapped_column(SmallInteger, default=0)
    data_sources: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    financials = relationship("FinancialData", back_populates="company", cascade="all, delete-orphan")
    persons = relationship("CompanyPerson", back_populates="company", cascade="all, delete-orphan")
    insolvency_cases = relationship("InsolvencyCase", back_populates="company", cascade="all, delete-orphan")
    court_cases = relationship("CourtCase", back_populates="company", cascade="all, delete-orphan")
    public_contracts = relationship("PublicContract", back_populates="company", cascade="all, delete-orphan")
    risk_score = relationship("RiskScore", back_populates="company", uselist=False)
    esg_score = relationship("ESGScore", back_populates="company", uselist=False)
    debts = relationship("CompanyDebt", back_populates="company", cascade="all, delete-orphan")
    eu_projects = relationship("EUProject", back_populates="company", cascade="all, delete-orphan")
    mentions = relationship("CompanyMention", back_populates="company", cascade="all, delete-orphan")
    trademarks = relationship("Trademark", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_companies_cui", "cui"),
        Index("idx_companies_caen", "caen_principal"),
        Index("idx_companies_judet_stare", "judet", "stare"),
        Index("idx_companies_active", "stare", postgresql_where=text("stare = 'ACTIVA'")),
        Index("idx_companies_insolvency", "id", postgresql_where=text("has_insolvency = TRUE")),
        Index("idx_companies_debts", "id", postgresql_where=text("has_debts = TRUE")),
        CheckConstraint("data_quality_score BETWEEN 0 AND 100", name="ck_data_quality"),
        CheckConstraint(
            "forma_juridica IN ('SRL','SA','PFA','RA','SNC','SCS','ALT')",
            name="ck_forma_juridica",
        ),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FINANCIAL DATA (annual balance sheets)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class FinancialData(Base):
    __tablename__ = "financial_data"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    an_fiscal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cifra_afaceri: Mapped[Optional[int]] = mapped_column(BigInteger)
    profit_net: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_active: Mapped[Optional[int]] = mapped_column(BigInteger)
    active_imobilizate: Mapped[Optional[int]] = mapped_column(BigInteger)
    active_circulante: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_datorii: Mapped[Optional[int]] = mapped_column(BigInteger)
    capitaluri_prop: Mapped[Optional[int]] = mapped_column(BigInteger)
    nr_angajati: Mapped[Optional[int]] = mapped_column(Integer)
    rata_lichiditate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    grad_indatorare: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    roa: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    profit_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    sursa: Mapped[str] = mapped_column(String(20), default="ANAF")

    company = relationship("Company", back_populates="financials")

    __table_args__ = (UniqueConstraint("company_id", "an_fiscal"),)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COMPANY PERSONS (associates, administrators)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class CompanyPerson(Base):
    __tablename__ = "company_persons"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    tip: Mapped[str] = mapped_column(String(20))
    nume_complet: Mapped[Optional[str]] = mapped_column(String(200))
    cnp_partial: Mapped[Optional[str]] = mapped_column(String(13))  # SHA-256 hashed â€“ GDPR #7
    procent_parti: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))
    data_start: Mapped[Optional[date]] = mapped_column(Date)
    data_sfarsit: Mapped[Optional[date]] = mapped_column(Date)
    activ: Mapped[bool] = mapped_column(Boolean, default=True)

    company = relationship("Company", back_populates="persons")

    __table_args__ = (
        CheckConstraint("tip IN ('ASOCIAT','ADMINISTRATOR','CENZOR','AUDITOR')", name="ck_person_tip"),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# INSOLVENCY CASES (BPI)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class InsolvencyCase(Base):
    __tablename__ = "insolvency_cases"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    nr_dosar_bpi: Mapped[Optional[str]] = mapped_column(String(50))
    nr_dosar_tribunal: Mapped[Optional[str]] = mapped_column(String(50))
    tip_procedura: Mapped[Optional[str]] = mapped_column(String(50))
    tribunal: Mapped[Optional[str]] = mapped_column(String(100))
    practician: Mapped[Optional[str]] = mapped_column(String(200))
    data_publicare: Mapped[Optional[date]] = mapped_column(Date)
    data_deschidere: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="ACTIV")
    continut_pdf_url: Mapped[Optional[str]] = mapped_column(String(500))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    company = relationship("Company", back_populates="insolvency_cases")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COURT CASES (ROLII)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class CourtCase(Base):
    __tablename__ = "court_cases"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    nr_dosar: Mapped[str] = mapped_column(String(50), unique=True)
    instanta: Mapped[Optional[str]] = mapped_column(String(200))
    instanta_oras: Mapped[Optional[str]] = mapped_column(String(100))
    obiect: Mapped[Optional[str]] = mapped_column(String(500))
    materie: Mapped[Optional[str]] = mapped_column(String(50))
    rol_firma: Mapped[Optional[str]] = mapped_column(String(20))
    parti: Mapped[Optional[dict]] = mapped_column(JSONB)
    stadiu: Mapped[Optional[str]] = mapped_column(String(100))
    solutie: Mapped[Optional[str]] = mapped_column(Text)
    data_solutie: Mapped[Optional[date]] = mapped_column(Date)
    data_dosar: Mapped[Optional[date]] = mapped_column(Date)
    ultima_actualizare: Mapped[Optional[date]] = mapped_column(Date)
    urmatorul_termen: Mapped[Optional[date]] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default="PORTAL_JUST")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="court_cases")
    hearings = relationship("LitigationHearing", back_populates="court_case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_court_cases_company", "company_id"),
        Index("idx_court_cases_termen", "urmatorul_termen", postgresql_where=text("urmatorul_termen >= '2000-01-01'")),
    )


class LitigationHearing(Base):
    __tablename__ = "litigation_hearings"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("court_cases.id", ondelete="CASCADE"))
    hearing_date: Mapped[date] = mapped_column(Date, nullable=False)
    hearing_time: Mapped[Optional[time]] = mapped_column(Time)
    sala: Mapped[Optional[str]] = mapped_column(String(30))
    status: Mapped[Optional[str]] = mapped_column(String(50))
    outcome: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    court_case = relationship("CourtCase", back_populates="hearings")

    __table_args__ = (
        Index("idx_hearings_case", "case_id"),
        Index("idx_hearings_date", "hearing_date", postgresql_where=text("hearing_date >= '2000-01-01'")),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PUBLIC CONTRACTS (SEAP)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class PublicContract(Base):
    __tablename__ = "public_contracts"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    autoritate_contractanta_cui: Mapped[Optional[str]] = mapped_column(String(20))
    autoritate_contractanta: Mapped[Optional[str]] = mapped_column(String(500))
    nr_contract: Mapped[Optional[str]] = mapped_column(String(100))
    titlu_contract: Mapped[Optional[str]] = mapped_column(Text)
    cod_cpv: Mapped[Optional[str]] = mapped_column(String(20))
    denumire_cpv: Mapped[Optional[str]] = mapped_column(String(200))
    tip_procedura: Mapped[Optional[str]] = mapped_column(String(50))
    valoare: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    moneda: Mapped[str] = mapped_column(String(5), default="RON")
    valoare_ron: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    data_atribuire: Mapped[Optional[date]] = mapped_column(Date)
    data_inceput: Mapped[Optional[date]] = mapped_column(Date)
    data_finalizare: Mapped[Optional[date]] = mapped_column(Date)
    durata_luni: Mapped[Optional[int]] = mapped_column(SmallInteger)
    seap_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="public_contracts")

    __table_args__ = (
        Index("idx_contracts_company", "company_id"),
        Index("idx_contracts_cpv", "cod_cpv"),
        Index("idx_contracts_data", "data_atribuire"),
    )


class PublicTenderActive(Base):
    __tablename__ = "public_tenders_active"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    authority_cui: Mapped[Optional[str]] = mapped_column(String(20))
    authority_name: Mapped[Optional[str]] = mapped_column(String(500))
    tender_number: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[Optional[str]] = mapped_column(Text)
    cpv_code: Mapped[Optional[str]] = mapped_column(String(20))
    cpv_name: Mapped[Optional[str]] = mapped_column(String(200))
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(5), default="RON")
    procedure_type: Mapped[Optional[str]] = mapped_column(String(50))
    deadline: Mapped[Optional[date]] = mapped_column(Date)
    submission_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    seap_url: Mapped[Optional[str]] = mapped_column(Text)
    caen_relevante: Mapped[Optional[list]] = mapped_column(ARRAY())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_tenders_deadline", "deadline", postgresql_where=text("deadline >= '2000-01-01'")),
        Index("idx_tenders_cpv", "cpv_code"),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# RISK SCORES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"), unique=True)
    score: Mapped[int] = mapped_column(Integer)
    rating: Mapped[Optional[str]] = mapped_column(String(5))
    scor_financiar: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    scor_legal: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    scor_fiscal: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    scor_comportamental: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    limita_credit: Mapped[Optional[int]] = mapped_column(BigInteger)
    probabilitate_insolventa: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    factori_risc: Mapped[Optional[dict]] = mapped_column(JSONB)
    calculat_la: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_versiune: Mapped[Optional[str]] = mapped_column(String(10))

    company = relationship("Company", back_populates="risk_score")

    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 100", name="ck_risk_score_range"),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ESG SCORES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ESGScore(Base):
    __tablename__ = "esg_scores"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"), index=True)
    score_e: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    score_s: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    score_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    score_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    e_emisii_co2: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    e_amenzi_mediu: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    e_certificari_iso: Mapped[Optional[bool]] = mapped_column(Boolean)
    s_stabilitate_angajati: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    s_salariu_vs_sector: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    s_litigii_munca: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    s_certificari_sociale: Mapped[Optional[bool]] = mapped_column(Boolean)
    g_stabilitate_management: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    g_transparenta_actionariat: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    g_conformitate_fiscala: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    g_dosare_penale: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    esg_rating: Mapped[Optional[str]] = mapped_column(String(5))
    csrd_relevant: Mapped[Optional[bool]] = mapped_column(Boolean)
    sfdr_categoria: Mapped[Optional[str]] = mapped_column(String(15))
    surse_date: Mapped[Optional[dict]] = mapped_column(JSONB)
    metodologie_versiune: Mapped[Optional[str]] = mapped_column(String(10))
    calculat_la: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="esg_score")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COMPANY DEBTS (ANAF datorii restante)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class CompanyDebt(Base):
    __tablename__ = "company_debts"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    suma_restanta: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    tip_datorie: Mapped[Optional[str]] = mapped_column(String(100))
    data_raportare: Mapped[Optional[date]] = mapped_column(Date)
    sursa: Mapped[str] = mapped_column(String(30), default="ANAF")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="debts")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXCHANGE RATES (BNR)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    rate_ron: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(10), default="BNR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("date", "currency"),)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EU PROJECTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class EUProject(Base):
    __tablename__ = "eu_projects"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    titlu: Mapped[Optional[str]] = mapped_column(Text)
    program_operational: Mapped[Optional[str]] = mapped_column(String(50))
    valoare_totala_ron: Mapped[Optional[int]] = mapped_column(BigInteger)
    finantare_ue_ron: Mapped[Optional[int]] = mapped_column(BigInteger)
    finantare_ue_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    cofinantare_ron: Mapped[Optional[int]] = mapped_column(BigInteger)
    data_aprobare: Mapped[Optional[date]] = mapped_column(Date)
    data_finalizare: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    sursa_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="eu_projects")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COMPANY MENTIONS (Monitor Oficial)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class CompanyMention(Base):
    __tablename__ = "company_mentions"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    tip_sectiune: Mapped[str] = mapped_column(String(5))
    tip_act: Mapped[Optional[str]] = mapped_column(String(100))
    nr_monitor: Mapped[Optional[str]] = mapped_column(String(50))
    data_publicare: Mapped[Optional[date]] = mapped_column(Date)
    continut_rezumat: Mapped[Optional[str]] = mapped_column(Text)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text)
    pdf_parsed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="mentions")

    __table_args__ = (
        CheckConstraint("tip_sectiune IN ('MO4','MO7')", name="ck_mention_sectiune"),
        Index("idx_mentions_company", "company_id", "data_publicare"),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ALERTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("organizations.id"))
    portfolio_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("monitored_portfolios.id"))
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("companies.id"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id"))
    tip_alerta: Mapped[Optional[str]] = mapped_column(String(50))
    titlu: Mapped[Optional[str]] = mapped_column(String(500))
    continut: Mapped[Optional[str]] = mapped_column(Text)
    alert_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    data_eveniment: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    citita: Mapped[bool] = mapped_column(Boolean, default=False)
    trimisa_email: Mapped[bool] = mapped_column(Boolean, default=False)
    trimisa_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    trimis_webhook: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_alerts_org_unread", "org_id", "created_at", postgresql_where=text("citita = FALSE")),
        Index("idx_alerts_company", "company_id", "created_at"),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MONITORED PORTFOLIOS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MonitoredPortfolio(Base):
    __tablename__ = "monitored_portfolios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    alert_email: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_webhook: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="portfolios")
    portfolio_companies = relationship("PortfolioCompany", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioCompany(Base):
    __tablename__ = "portfolio_companies"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("monitored_portfolios.id", ondelete="CASCADE"))
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[Optional[str]] = mapped_column(Text)

    portfolio = relationship("MonitoredPortfolio", back_populates="portfolio_companies")

    __table_args__ = (UniqueConstraint("portfolio_id", "company_id"),)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SAVED SEARCHES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    filters_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    notify_new: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_saved_searches_user", "user_id"),
        Index("idx_saved_searches_notify", "notify_new", postgresql_where=text("notify_new = TRUE")),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FRAUD GRAPH
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class EntityRelation(Base):
    __tablename__ = "entity_relations"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))
    sursa: Mapped[Optional[str]] = mapped_column(String(20))
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("source_type IN ('COMPANY','PERSON')", name="ck_rel_source_type"),
        CheckConstraint("target_type IN ('COMPANY','PERSON')", name="ck_rel_target_type"),
        Index("idx_relations_source", "source_type", "source_id"),
        Index("idx_relations_target", "target_type", "target_id"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("companies.id"))
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(10))
    company_ids: Mapped[Optional[list]] = mapped_column(ARRAY())
    person_hashes: Mapped[Optional[list]] = mapped_column(ARRAY())
    descriere: Mapped[Optional[str]] = mapped_column(Text)
    dovezi: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    detectat_la: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rezolvat_la: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_fraud_severity"),
        Index("idx_fraud_alerts_type", "alert_type", "severity"),
    )


class GraphMetric(Base):
    __tablename__ = "graph_metrics"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("companies.id"))
    entity_type: Mapped[Optional[str]] = mapped_column(String(20))
    entity_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    pagerank_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    betweenness: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    degree_in: Mapped[Optional[int]] = mapped_column(Integer)
    degree_out: Mapped[Optional[int]] = mapped_column(Integer)
    community_id: Mapped[Optional[int]] = mapped_column(Integer)
    suspicion_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    calculat_la: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ESG RAW DATA & ENVIRONMENTAL FINES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ESGRawData(Base):
    __tablename__ = "esg_raw_data"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    sursa: Mapped[Optional[str]] = mapped_column(String(50))
    categorie: Mapped[Optional[str]] = mapped_column(String(10))
    indicator: Mapped[Optional[str]] = mapped_column(String(100))
    valoare: Mapped[Optional[str]] = mapped_column(Text)
    unitate: Mapped[Optional[str]] = mapped_column(String(30))
    an_referinta: Mapped[Optional[int]] = mapped_column(SmallInteger)
    data_colectare: Mapped[Optional[date]] = mapped_column(Date)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONB)


class EnvironmentalFine(Base):
    __tablename__ = "environmental_fines"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    autoritate: Mapped[Optional[str]] = mapped_column(String(100))
    suma_ron: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    motiv: Mapped[Optional[str]] = mapped_column(Text)
    data_amenda: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[Optional[str]] = mapped_column(String(20))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NEW COMPANIES FEED
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class NewCompanyFeed(Base):
    __tablename__ = "new_companies_feed"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    registration_date: Mapped[Optional[date]] = mapped_column(Date)
    feed_date: Mapped[date] = mapped_column(Date, server_default=text("CURRENT_DATE"))
    sursa: Mapped[Optional[str]] = mapped_column(String(30))
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company")

    __table_args__ = (
        Index("idx_new_companies_feed_date", "feed_date"),
        Index("idx_new_companies_notified", "is_notified", postgresql_where=text("is_notified = FALSE")),
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# REPORT EXPORTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("organizations.id"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id"))
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("companies.id"))
    export_type: Mapped[Optional[str]] = mapped_column(String(30))
    format: Mapped[Optional[str]] = mapped_column(String(10))
    task_id: Mapped[Optional[str]] = mapped_column(String(100))
    filters_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    file_url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    credits_consumed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AUDIT LOG (GDPR compliant)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("organizations.id"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(Text)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DATA SOURCE SYNC LOG
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class DataSourceSyncLog(Base):
    __tablename__ = "data_source_sync_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sync_type: Mapped[Optional[str]] = mapped_column(String(20))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_sync_log_source", "source_name", "started_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# TRADEMARKS & PATENTS (OSIM)
# ═══════════════════════════════════════════════════════════════════════════

class Trademark(Base):
    __tablename__ = "trademarks"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    tip: Mapped[str] = mapped_column(String(20), default="marca")
    denumire: Mapped[Optional[str]] = mapped_column(String(500))
    nr_inregistrare: Mapped[Optional[str]] = mapped_column(String(50))
    titular: Mapped[Optional[str]] = mapped_column(String(500))
    data_inregistrare: Mapped[Optional[date]] = mapped_column(Date)
    data_expirare: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[Optional[str]] = mapped_column(String(30))
    clase_nisa: Mapped[Optional[dict]] = mapped_column(JSONB)
    imagine_url: Mapped[Optional[str]] = mapped_column(Text)
    sursa: Mapped[str] = mapped_column(String(20), default="OSIM")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company")

    __table_args__ = (
        Index("idx_trademarks_company", "company_id"),
        Index("idx_trademarks_nr", "nr_inregistrare"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# STATISTICAL SNAPSHOTS (INS)
# ═══════════════════════════════════════════════════════════════════════════

class StatisticSnapshot(Base):
    __tablename__ = "statistic_snapshots"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    indicator_code: Mapped[str] = mapped_column(String(30), nullable=False)
    indicator_name: Mapped[Optional[str]] = mapped_column(String(200))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    judet: Mapped[Optional[str]] = mapped_column(String(50))
    caen_code: Mapped[Optional[str]] = mapped_column(String(10))
    period: Mapped[Optional[str]] = mapped_column(String(20))
    measure_unit: Mapped[Optional[str]] = mapped_column(String(30))
    value_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    sursa: Mapped[str] = mapped_column(String(20), default="INS")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_stats_indicator", "indicator_code", "period"),
        Index("idx_stats_judet", "judet"),
        Index("idx_stats_caen", "caen_code"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CIP INCIDENTS (placeholder — requires BNR contract)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class CIPIncident(Base):
    __tablename__ = "cip_incidents"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"))
    incident_type: Mapped[Optional[str]] = mapped_column(String(30))
    incident_date: Mapped[Optional[date]] = mapped_column(Date)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(5), default="RON")
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    source: Mapped[Optional[str]] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# API MARKETPLACE — Usage Logs & Webhooks
# ═══════════════════════════════════════════════════════════════════════════

class ApiUsageLog(Base):
    __tablename__ = "api_usage_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("api_keys.id", ondelete="SET NULL"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id", ondelete="SET NULL"))
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET")
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    request_body_size: Mapped[Optional[int]] = mapped_column(Integer)
    response_body_size: Mapped[Optional[int]] = mapped_column(Integer)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_api_usage_user", "user_id", "created_at"),
        Index("idx_api_usage_key", "api_key_id", "created_at"),
    )


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    events: Mapped[dict] = mapped_column(JSONB, default=[])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deliveries: Mapped[int] = mapped_column(Integer, default=0)
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_status_code: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_webhook_org", "org_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# BLOCKCHAIN AUDIT — Hash Chain, Document Hashes, Custody Records
# ═══════════════════════════════════════════════════════════════════════════

class BlockchainBlock(Base):
    __tablename__ = "blockchain_blocks"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    nonce: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentHash(Base):
    __tablename__ = "document_hashes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    document_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_name: Mapped[str] = mapped_column(String(500), nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id", ondelete="SET NULL"))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    block_index: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_doc_hash", "document_hash"),
    )


class CustodyRecord(Base):
    __tablename__ = "custody_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(), ForeignKey("users.id", ondelete="SET NULL"))
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    block_index: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_custody_company", "company_id", "created_at"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPANY BALANCE SHEETS  (bilanţuri MF/ANAF bulk import)
# ══════════════════════════════════════════════════════════════════════════════

class CompanyBalanceSheet(Base):
    """Annual financial statements imported in bulk from MF/ANAF open-data files.

    Uses `cui` directly (no FK) so that records for companies not yet in the
    `companies` table can be stored without constraint errors.
    """
    __tablename__ = "company_balance_sheets"

    id: Mapped[int] = mapped_column(CompatBigInt(), primary_key=True, autoincrement=True)
    cui: Mapped[int] = mapped_column(Integer, nullable=False)
    an_fiscal: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # ── Profit & Loss ────────────────────────────────────────────────
    cifra_afaceri: Mapped[Optional[int]] = mapped_column(BigInteger)        # RON
    venituri_totale: Mapped[Optional[int]] = mapped_column(BigInteger)      # RON
    cheltuieli_totale: Mapped[Optional[int]] = mapped_column(BigInteger)    # RON
    profit_brut: Mapped[Optional[int]] = mapped_column(BigInteger)          # RON
    pierdere_bruta: Mapped[Optional[int]] = mapped_column(BigInteger)       # RON (absolute)
    profit_net: Mapped[Optional[int]] = mapped_column(BigInteger)           # RON
    pierdere_neta: Mapped[Optional[int]] = mapped_column(BigInteger)        # RON (absolute)

    # ── Balance Sheet ────────────────────────────────────────────────
    total_active: Mapped[Optional[int]] = mapped_column(BigInteger)         # RON
    active_imobilizate: Mapped[Optional[int]] = mapped_column(BigInteger)   # RON
    active_circulante: Mapped[Optional[int]] = mapped_column(BigInteger)    # RON
    capitaluri_proprii: Mapped[Optional[int]] = mapped_column(BigInteger)   # RON
    datorii_totale: Mapped[Optional[int]] = mapped_column(BigInteger)       # RON
    datorii_termen_lung: Mapped[Optional[int]] = mapped_column(BigInteger)  # RON

    # ── Headcount ────────────────────────────────────────────────────
    nr_salariati: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Metadata ─────────────────────────────────────────────────────
    sursa: Mapped[str] = mapped_column(String(20), default="MF_BULK")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("cui", "an_fiscal", name="uq_balance_sheet_cui_year"),
        Index("idx_balance_sheets_cui", "cui"),
        Index("idx_balance_sheets_year", "an_fiscal"),
    )
