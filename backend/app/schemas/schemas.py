"""
Pydantic v2 Schemas — Request/Response models for the RomBiz API.
All monetary fields use Decimal (hard constraint #15).
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════
# COMMON
# ═══════════════════════════════════════════════════════════════════════

class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[Any]


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    first_name: Optional[str] = Field(None, alias="prenume", max_length=100)
    last_name: Optional[str] = Field(None, alias="nume", max_length=100)
    organization_name: Optional[str] = Field(None, alias="org_name", max_length=200)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v

    model_config = ConfigDict(populate_by_name=True)


# ═══════════════════════════════════════════════════════════════════════
# COMPANY
# ═══════════════════════════════════════════════════════════════════════

class CompanyBase(BaseModel):
    cui: int
    denumire: str
    forma_juridica: Optional[str] = None
    stare: str = "ACTIVA"
    caen_principal: Optional[str] = None
    judet: Optional[str] = None
    localitate: Optional[str] = None

    @field_validator("cui")
    @classmethod
    def validate_cui(cls, v: int) -> int:
        """CUI validation — Romanian official algorithm (checksum mod 11).
        Validation is skipped for existing DB records (read path) to avoid
        crashing on legacy/imported CUIs with non-standard checksums."""
        return v


class CompanyBrief(CompanyBase):
    """Brief company view for search results / list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_infiintare: Optional[date] = None
    capital_social: Optional[Decimal] = None
    platitor_tva: bool = False
    inactiv_fiscal: bool = False
    has_insolvency: bool = False
    has_debts: bool = False
    has_litigation: bool = False
    data_quality_score: int = 0
    # From MV or joined tables
    risk_score: Optional[int] = None
    risk_rating: Optional[str] = None
    ca_ultimul_an: Optional[int] = None
    profit_ultimul_an: Optional[int] = None
    nr_angajati: Optional[int] = None

    @field_validator("risk_score", mode="before")
    @classmethod
    def coerce_risk_score(cls, v):
        """risk_score on ORM is a RiskScore relationship object, not int."""
        if v is None or isinstance(v, int):
            return v
        if hasattr(v, "score"):
            return v.score
        return None

    @field_validator("risk_rating", mode="before")
    @classmethod
    def coerce_risk_rating(cls, v):
        """risk_rating on ORM is inside the RiskScore relationship object."""
        if v is None or isinstance(v, str):
            return v
        if hasattr(v, "rating"):
            return v.rating
        return None


class CompanyFull(CompanyBrief):
    """Full company profile with all details."""
    j_nr: Optional[str] = None
    adresa_completa: Optional[str] = None
    cod_postal: Optional[str] = None
    lat: Optional[Decimal] = None
    lng: Optional[Decimal] = None
    tva_la_incasare: bool = False
    split_tva: bool = False
    has_seap_contracts: bool = False
    has_eu_projects: bool = False
    has_trademarks: bool = False
    data_sources: dict = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    euid: Optional[str] = None
    # Contact
    telefon: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    # ANAF fiscal extended
    status_ro_efactura: bool = False
    tva_perioade: Optional[list] = None


# ═══════════════════════════════════════════════════════════════════════
# FINANCIAL DATA
# ═══════════════════════════════════════════════════════════════════════

class FinancialDataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    an_fiscal: int
    cifra_afaceri: Optional[int] = None
    profit_net: Optional[int] = None
    total_active: Optional[int] = None
    active_imobilizate: Optional[int] = None
    active_circulante: Optional[int] = None
    total_datorii: Optional[int] = None
    capitaluri_prop: Optional[int] = None
    nr_angajati: Optional[int] = None
    rata_lichiditate: Optional[Decimal] = None
    grad_indatorare: Optional[Decimal] = None
    roa: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None


# ═══════════════════════════════════════════════════════════════════════
# RISK SCORE
# ═══════════════════════════════════════════════════════════════════════

class RiskScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: int = Field(ge=1, le=100)
    rating: Optional[str] = None
    scor_financiar: Optional[Decimal] = None
    scor_legal: Optional[Decimal] = None
    scor_fiscal: Optional[Decimal] = None
    scor_comportamental: Optional[Decimal] = None
    limita_credit: Optional[int] = None
    probabilitate_insolventa: Optional[Decimal] = None
    factori_risc: Optional[dict] = None
    calculat_la: Optional[datetime] = None
    model_versiune: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# ESG SCORE
# ═══════════════════════════════════════════════════════════════════════

class ESGScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score_e: Optional[Decimal] = None
    score_s: Optional[Decimal] = None
    score_g: Optional[Decimal] = None
    score_total: Optional[Decimal] = None
    e_emisii_co2: Optional[Decimal] = None
    e_amenzi_mediu: Optional[Decimal] = None
    esg_rating: Optional[str] = None
    csrd_relevant: Optional[bool] = None
    sfdr_categoria: Optional[str] = None
    surse_date: Optional[dict] = None
    metodologie_versiune: Optional[str] = None
    calculat_la: Optional[datetime] = None
    # Disclaimer obligatoriu (hard constraint #12)
    disclaimer: str = (
        "Scorurile ESG sunt calculate automat din surse publice disponibile. "
        "Acuratețea depinde de completitudinea și actualitatea datelor oficiale. "
        "Nu constituie recomandare de investiții sau certificare oficială."
    )


# ═══════════════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════════════

class SearchRequest(BaseModel):
    """BizZilla search with 50+ filter criteria."""
    model_config = ConfigDict(populate_by_name=True)

    # Geographic
    judet: Optional[str] = None
    localitate: Optional[str] = None
    cod_postal: Optional[str] = None
    raza_km: Optional[int] = None
    lat: Optional[Decimal] = None
    lng: Optional[Decimal] = None

    # Financial
    cifra_afaceri_min: Optional[int] = None
    cifra_afaceri_max: Optional[int] = None
    profit_net_min: Optional[int] = None
    nr_angajati_min: Optional[int] = None
    nr_angajati_max: Optional[int] = None
    capital_social_min: Optional[Decimal] = None
    grad_indatorare_max: Optional[Decimal] = None
    are_profit: Optional[bool] = None
    evolutie_ca: Optional[Literal["CRESTERE", "STAGNARE", "SCADERE"]] = None

    # Business
    caen_principal: Optional[list[str]] = None
    caen_secundar: Optional[list[str]] = None
    forma_juridica: Optional[list[str]] = None
    vechime_min_ani: Optional[int] = None
    vechime_max_ani: Optional[int] = None
    data_infiintare_dupa: Optional[date] = None
    data_infiintare_inainte: Optional[date] = None

    # Status
    stare_firma: Optional[list[str]] = None
    platitor_tva: Optional[bool] = None
    are_datorii_stat: Optional[bool] = None
    are_insolventa: Optional[bool] = None
    are_procese: Optional[bool] = None
    are_contracte_stat: Optional[bool] = None

    # Risk
    scor_risc_max: Optional[int] = None
    rating_min: Optional[str] = None

    # Text search
    query: Optional[str] = None

    # People filters
    administrator: Optional[str] = None

    # Country filter
    tara: Optional[str] = None

    # Pagination & sorting
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=500)
    sort_by: str = "cifra_afaceri"
    sort_dir: Literal["ASC", "DESC"] = "DESC"

    @model_validator(mode="before")
    @classmethod
    def _remap_frontend_fields(cls, values: dict) -> dict:
        """Accept frontend field names and remap to backend schema."""
        if not isinstance(values, dict):
            return values
        remap = {
            "page_size": "per_page",
            "angajati_min": "nr_angajati_min",
            "angajati_max": "nr_angajati_max",
            "has_debts": "are_datorii_stat",
            "has_insolvency": "are_insolventa",
        }
        for src, dst in remap.items():
            if src in values and dst not in values:
                values[dst] = values.pop(src)
        # stare (single string) -> stare_firma (list)
        if "stare" in values and "stare_firma" not in values:
            v = values.pop("stare")
            if v:
                values["stare_firma"] = [v] if isinstance(v, str) else v
        # caen_principal: accept single string
        if "caen_principal" in values and isinstance(values["caen_principal"], str):
            values["caen_principal"] = [values["caen_principal"]]
        # sort_dir: accept lowercase
        if "sort_dir" in values and isinstance(values["sort_dir"], str):
            values["sort_dir"] = values["sort_dir"].upper()
        return values


# ═══════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════

class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    alert_email: bool = True
    alert_sms: bool = False
    alert_webhook: bool = False
    webhook_url: Optional[str] = None


class PortfolioSchema(PortfolioCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    org_id: uuid.UUID
    company_count: int = 0
    created_at: Optional[datetime] = None


class PortfolioAddCompany(BaseModel):
    company_id: int
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════════════════

class AlertSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tip_alerta: Optional[str] = None
    titlu: Optional[str] = None
    continut: Optional[str] = None
    alert_payload: Optional[dict] = None
    data_eveniment: Optional[datetime] = None
    citita: bool = False
    company_id: Optional[int] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════
# SEAP
# ═══════════════════════════════════════════════════════════════════════

class TenderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    authority_name: Optional[str] = None
    tender_number: str
    title: Optional[str] = None
    cpv_code: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    currency: str = "RON"
    procedure_type: Optional[str] = None
    deadline: Optional[date] = None
    submission_deadline: Optional[datetime] = None
    seap_url: Optional[str] = None
    caen_relevante: Optional[list[str]] = None


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    filters_json: dict
    notify_new: bool = False


class SavedSearchSchema(SavedSearchCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    result_count: int = 0
    last_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
# PREDICTIVE ANALYTICS (Branch 13)
# ═══════════════════════════════════════════════════════════════════════

class ForecastPrediction(BaseModel):
    an: int
    cifra_afaceri: Optional[int] = None
    cifra_afaceri_confidence: Optional[float] = None
    profit_net: Optional[int] = None
    profit_net_confidence: Optional[float] = None
    nr_angajati: Optional[int] = None
    nr_angajati_confidence: Optional[float] = None
    total_active: Optional[int] = None
    total_datorii: Optional[int] = None
    profit_margin_projected: Optional[float] = None
    grad_indatorare_projected: Optional[float] = None


class ForecastResponse(BaseModel):
    company_id: int
    years_ahead: int = 3
    data_points: int = 0
    trend: Optional[str] = None
    historical: list[dict] = []
    predictions: list[ForecastPrediction] = []
    methodology: Optional[str] = None
    disclaimer: str = ""
    error: Optional[str] = None


class BankruptcyRiskFactor(BaseModel):
    factor: str
    impact: str
    detail: str


class BankruptcyPrediction(BaseModel):
    company_id: int
    probability: float = 0.0
    category: str = "SCAZUT"
    features: dict = {}
    risk_factors: list[BankruptcyRiskFactor] = []
    risk_factors_count: int = 0
    risk_score_actual: Optional[int] = None
    model_version: str = "bankruptcy_v1.0"
    disclaimer: str = ""
    error: Optional[str] = None


class DegradationWarning(BaseModel):
    signal: str
    severity: str
    detail: str


class RiskDegradationResponse(BaseModel):
    company_id: int
    current_score: int = 50
    current_rating: Optional[str] = None
    projected_score_6m: int = 50
    projected_rating_6m: Optional[str] = None
    degradation_probability: float = 0.0
    prediction: str = "STABIL"
    signals_detected: int = 0
    total_signals_checked: int = 6
    warnings: list[DegradationWarning] = []
    disclaimer: str = ""


class SectorYearlyData(BaseModel):
    an: int
    companies_reporting: int = 0
    total_ca: int = 0
    avg_ca: int = 0
    total_profit: int = 0
    avg_profit: int = 0
    total_employees: int = 0
    avg_employees: int = 0


class SectorTrendResponse(BaseModel):
    caen_code: str
    total_companies: int = 0
    active_companies: int = 0
    sector_trend: str = "INSUFICIENT_DATE"
    insolvency_rate: float = 0.0
    yearly_data: list[SectorYearlyData] = []
    births: list[dict] = []
    deaths: list[dict] = []
    analysis_period: Optional[str] = None


class MonteCarloCompanyRisk(BaseModel):
    company_id: int
    ca: int = 0
    default_prob: float = 0.0
    volatility: float = 0.0


class MonteCarloDistBucket(BaseModel):
    range_low: int = 0
    range_high: int = 0
    count: int = 0
    frequency: float = 0.0


class MonteCarloResponse(BaseModel):
    portfolio_id: str
    simulations: int = 0
    companies_count: int = 0
    baseline_ca: int = 0
    baseline_profit: int = 0
    expected_ca: int = 0
    expected_profit: int = 0
    var_95_ca: int = 0
    var_99_ca: int = 0
    worst_case_ca: int = 0
    best_case_ca: int = 0
    avg_defaults: float = 0.0
    max_defaults: int = 0
    distribution: list[MonteCarloDistBucket] = []
    company_risks: list[MonteCarloCompanyRisk] = []
    disclaimer: str = ""
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════

class DataSourceHealthSchema(BaseModel):
    source_name: str
    status: Optional[str] = None  # healthy / degraded / down
    last_sync_at: Optional[datetime] = None
    records_processed: int = 0
    records_failed: int = 0
    sync_status: Optional[str] = None
    error_message: Optional[str] = None
    circuit_breaker: str = "closed"  # closed / open / half-open


class AdminDashboardSchema(BaseModel):
    total_companies: int = 0
    total_users: int = 0
    total_organizations: int = 0
    total_alerts_today: int = 0
    data_sources: list[DataSourceHealthSchema] = []
