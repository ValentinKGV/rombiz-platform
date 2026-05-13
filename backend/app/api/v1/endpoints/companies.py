"""
Company endpoints — profile, financial, legal, persons, etc.
11 tabs worth of data.
"""
from __future__ import annotations

from typing import Optional

from decimal import Decimal
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import (
    Company, FinancialData, CompanyPerson, InsolvencyCase,
    CourtCase, PublicContract, EUProject, CompanyMention,
    CompanyDebt, RiskScore, ESGScore, CompanyBalanceSheet,
    Trademark,
)
from app.schemas.schemas import CompanyFull, CompanyBrief, FinancialDataSchema

router = APIRouter()


@router.post("/import/{cui}", response_model=CompanyBrief)
async def import_company_from_anaf(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Import a company from ANAF by CUI.
    If the company already exists in DB, returns it.
    Otherwise fetches from ANAF, creates it in DB, and returns it.
    """
    # Check if already in DB
    result = await db.execute(
        select(Company).where(Company.cui == cui).options(selectinload(Company.risk_score))
    )
    company = result.scalar_one_or_none()
    if company:
        return CompanyBrief.model_validate(company)

    # Fetch from ANAF via ONRCCollector
    from app.collectors.onrc import ONRCCollector
    collector = ONRCCollector()
    data = await collector.fetch_single(cui)

    if not data or not data.get("denumire"):
        raise HTTPException(
            status_code=404,
            detail=f"CUI {cui} nu a fost găsit în ANAF/ONRC.",
        )

    # Map ANAF data → Company model
    stare_raw = (data.get("stare_firma") or "ACTIVA").upper()
    stare = stare_raw if stare_raw in ("ACTIVA", "INACTIVA", "RADIAT", "SUSPENDAT") else "ACTIVA"

    capital_raw = data.get("capital_social")
    capital = Decimal(str(capital_raw)) if capital_raw is not None else None

    # forma_juridica from ANAF can be full description ("PERSOANA FIZICA AUTORIZATA", "SOCIETATE ")
    # DB CHECK constraint only allows: SRL, SA, PFA, RA, SNC, SCS, ALT
    # Also try to extract from the company name (S.R.L., S.A. etc.)
    _ALLOWED = {"SRL", "SA", "PFA", "RA", "SNC", "SCS"}
    _FORMA_MAP = {
        "S.R.L": "SRL", "SRL": "SRL",
        "S.A.": "SA", " SA ": "SA", " SA,": "SA",
        "S.N.C": "SNC", "SNC": "SNC",
        "S.C.S": "SCS", "SCS": "SCS",
        "AUTORIZATA": "PFA", "P.F.A": "PFA", "PFA": "PFA",
        "REGII": "RA", " RA ": "RA",
    }

    def _detect_forma(text: str) -> str:
        upper = text.upper()
        for key, val in _FORMA_MAP.items():
            if key in upper:
                return val
        return "ALT"

    forma_raw = data.get("forma_juridica") or ""
    # Try raw forma_juridica first, then fall back to company name
    forma_juridica = _detect_forma(forma_raw) if forma_raw.strip() else None
    if not forma_juridica or forma_juridica == "ALT":
        # Check denomination — often more reliable (e.g. "NINE ... S.R.L.")
        from_denumire = _detect_forma(data.get("denumire") or "")
        if from_denumire != "ALT":
            forma_juridica = from_denumire
        else:
            forma_juridica = "ALT"

    # cod_postal: empty string → None
    cod_postal_raw = data.get("cod_postal") or None
    if cod_postal_raw == "":
        cod_postal_raw = None

    # Parse data_infiintare — ANAF may return string "YYYY-MM-DD" or date object
    raw_date = data.get("data_infiintare")
    if isinstance(raw_date, str) and raw_date:
        try:
            data_infiintare = date_type.fromisoformat(raw_date[:10])
        except ValueError:
            data_infiintare = None
    elif isinstance(raw_date, date_type):
        data_infiintare = raw_date
    else:
        data_infiintare = None

    company = Company(
        cui=cui,
        denumire=data["denumire"],
        j_nr=data.get("nr_reg_comert"),
        forma_juridica=forma_juridica,
        stare=stare,
        data_infiintare=data_infiintare,
        caen_principal=data.get("cod_caen_principal"),
        capital_social=capital,
        adresa_completa=data.get("sediu_social"),
        judet=data.get("judet"),
        localitate=data.get("localitate"),
        cod_postal=cod_postal_raw,
        platitor_tva=bool(data.get("tva_activ", False)),
        tva_la_incasare=bool(data.get("tva_la_incasare", False)),
        split_tva=bool(data.get("split_tva", False)),
        inactiv_fiscal=bool(data.get("inactiv_fiscal", False)),
        # has_insolvency stays False — insolvency data comes from BPI, not ANAF
        has_insolvency=False,
        data_sources={"anaf": True, "berc": data.get("berc_enriched", False)},
        data_quality_score=50,
    )
    db.add(company)
    await db.commit()
    # Re-fetch with relationships loaded to avoid MissingGreenlet on risk_score
    result2 = await db.execute(
        select(Company).where(Company.id == company.id).options(selectinload(Company.risk_score))
    )
    company = result2.scalar_one()

    return CompanyBrief.model_validate(company)


@router.get("/{cui}", response_model=CompanyFull)
async def get_company(
    cui: int,
    include: Optional[list[str]] = Query(
        default=None,
        description="Optional sections: financial,legal,risk,persons,contracts,esg"
    ),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get complete company profile by CUI."""
    result = await db.execute(
        select(Company).where(Company.cui == cui).options(selectinload(Company.risk_score))
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with CUI {cui} not found")

    return CompanyFull.model_validate(company)


@router.get("/{cui}/financial", response_model=list[FinancialDataSchema])
async def get_company_financials(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get financial data (balance sheets) for all available years.

    Primary source: financial_data table (detailed, with computed ratios).
    Fallback: company_balance_sheets table (MF/ANAF bulk import).
    """
    result = await db.execute(
        select(Company).where(Company.cui == cui)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company.id)
        .order_by(FinancialData.an_fiscal.desc())
    )
    rows = result.scalars().all()

    if rows:
        return [FinancialDataSchema.model_validate(fd) for fd in rows]

    # Fallback: read from bulk-imported balance sheets (MF/ANAF open data)
    result2 = await db.execute(
        select(CompanyBalanceSheet)
        .where(CompanyBalanceSheet.cui == cui)
        .order_by(CompanyBalanceSheet.an_fiscal.desc())
    )
    bulk_rows = result2.scalars().all()

    def _ratio(num, den):
        try:
            return round(num / den * 100, 2) if den and den != 0 else None
        except Exception:
            return None

    result3 = []
    for bs in bulk_rows:
        ta   = bs.total_active
        cp   = bs.capitaluri_proprii
        pn   = bs.profit_net
        ca   = bs.cifra_afaceri
        dat  = bs.datorii_totale
        ac   = bs.active_circulante
        ai   = bs.active_imobilizate
        result3.append(FinancialDataSchema(
            an_fiscal=bs.an_fiscal,
            cifra_afaceri=ca,
            profit_net=pn,
            total_active=ta,
            active_imobilizate=ai,
            active_circulante=ac,
            total_datorii=dat,
            capitaluri_prop=cp,
            nr_angajati=bs.nr_salariati,
            roa=_ratio(pn, ta),
            roe=_ratio(pn, cp),
            profit_margin=_ratio(pn, ca),
            grad_indatorare=_ratio(dat, cp) if cp and cp > 0 else None,
            rata_lichiditate=round(ac / dat, 2) if ac and dat and dat > 0 else None,
        ))
    return result3


@router.get("/{cui}/persons")
async def get_company_persons(
    cui: int,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get associates and administrators."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = select(CompanyPerson).where(CompanyPerson.company_id == company.id)
    if active_only:
        query = query.where(CompanyPerson.activ == True)

    result = await db.execute(query.order_by(CompanyPerson.tip, CompanyPerson.data_start.desc()))
    persons = result.scalars().all()

    return [
        {
            "id": p.id,
            "tip": p.tip,
            "nume_complet": p.nume_complet,
            "procent_parti": float(p.procent_parti) if p.procent_parti else None,
            "data_start": p.data_start,
            "data_sfarsit": p.data_sfarsit,
            "activ": p.activ,
        }
        for p in persons
    ]


@router.get("/{cui}/insolvency")
async def get_company_insolvency(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get insolvency cases from BPI."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(InsolvencyCase)
        .where(InsolvencyCase.company_id == company.id)
        .order_by(InsolvencyCase.data_publicare.desc())
    )
    return [
        {
            "nr_dosar_bpi": ic.nr_dosar_bpi,
            "tip_procedura": ic.tip_procedura,
            "tribunal": ic.tribunal,
            "practician": ic.practician,
            "data_deschidere": ic.data_deschidere,
            "status": ic.status,
        }
        for ic in result.scalars().all()
    ]


@router.get("/{cui}/court-cases")
async def get_company_court_cases(
    cui: int,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get court cases from ROLII."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    offset = (page - 1) * per_page
    result = await db.execute(
        select(CourtCase)
        .where(CourtCase.company_id == company.id)
        .order_by(CourtCase.data_dosar.desc())
        .offset(offset)
        .limit(per_page)
    )
    return [
        {
            "nr_dosar": cc.nr_dosar,
            "instanta": cc.instanta,
            "obiect": cc.obiect,
            "materie": cc.materie,
            "rol_firma": cc.rol_firma,
            "stadiu": cc.stadiu,
            "urmatorul_termen": cc.urmatorul_termen,
        }
        for cc in result.scalars().all()
    ]


@router.get("/{cui}/contracts")
async def get_company_contracts(
    cui: int,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get public contracts (SEAP)."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    offset = (page - 1) * per_page
    result = await db.execute(
        select(PublicContract)
        .where(PublicContract.company_id == company.id)
        .order_by(PublicContract.data_atribuire.desc())
        .offset(offset)
        .limit(per_page)
    )
    return [
        {
            "nr_contract": pc.nr_contract,
            "autoritate_contractanta": pc.autoritate_contractanta,
            "titlu_contract": pc.titlu_contract,
            "valoare_ron": float(pc.valoare_ron) if pc.valoare_ron else None,
            "data_atribuire": pc.data_atribuire,
            "cod_cpv": pc.cod_cpv,
        }
        for pc in result.scalars().all()
    ]


@router.get("/{cui}/eu-projects")
async def get_company_eu_projects(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get EU-funded projects."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(EUProject)
        .where(EUProject.company_id == company.id)
        .order_by(EUProject.data_aprobare.desc())
    )
    return [
        {
            "titlu": ep.titlu,
            "program_operational": ep.program_operational,
            "valoare_totala_ron": ep.valoare_totala_ron,
            "finantare_ue_pct": float(ep.finantare_ue_pct) if ep.finantare_ue_pct else None,
            "status": ep.status,
            "data_aprobare": ep.data_aprobare,
        }
        for ep in result.scalars().all()
    ]


@router.get("/{cui}/mentions")
async def get_company_mentions(
    cui: int,
    sectiune: Optional[str] = Query(default=None, description="MO4 or MO7"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get Monitor Oficial mentions."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = select(CompanyMention).where(CompanyMention.company_id == company.id)
    if sectiune:
        query = query.where(CompanyMention.tip_sectiune == sectiune)

    result = await db.execute(query.order_by(CompanyMention.data_publicare.desc()))
    return [
        {
            "tip_sectiune": m.tip_sectiune,
            "tip_act": m.tip_act,
            "data_publicare": m.data_publicare,
            "continut_rezumat": m.continut_rezumat,
        }
        for m in result.scalars().all()
    ]


@router.get("/{cui}/trademarks")
async def get_company_trademarks(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get OSIM trademarks & patents for a company."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(
        select(Trademark)
        .where(Trademark.company_id == company.id)
        .order_by(Trademark.data_inregistrare.desc())
    )
    trademarks = result.scalars().all()
    return [
        {
            "tip": t.tip,
            "denumire": t.denumire,
            "nr_inregistrare": t.nr_inregistrare,
            "titular": t.titular,
            "data_inregistrare": t.data_inregistrare,
            "data_expirare": t.data_expirare,
            "status": t.status,
            "clase_nisa": t.clase_nisa,
        }
        for t in trademarks
    ]


@router.get("/{cui}/bvb")
async def get_company_bvb(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get BVB stock market data for a company (if listed)."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bvb_data = (company.data_sources or {}).get("bvb")
    if not bvb_data:
        return {"listed": False}
    return {"listed": True, **bvb_data}


@router.get("/{cui}/asf")
async def get_company_asf(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get ASF regulatory data for a company (if supervised)."""
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    asf_data = (company.data_sources or {}).get("asf")
    sanctions = (company.data_sources or {}).get("asf_sanctions", [])
    if not asf_data and not sanctions:
        return {"supervised": False}
    return {"supervised": True, "autorizatie": asf_data, "sanctiuni": sanctions}


@router.post("/batch")
async def batch_company_lookup(
    cuis: list[int],
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Batch lookup — max 500 CUIs per request."""
    if len(cuis) > 500:
        raise HTTPException(status_code=400, detail="Max 500 CUIs per batch request")

    result = await db.execute(
        select(Company).where(Company.cui.in_(cuis))
    )
    companies = result.scalars().all()
    return [CompanyBrief.model_validate(c) for c in companies]
