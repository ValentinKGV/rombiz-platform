"""
Search endpoints — advanced multi-filter search.

v2 Endpoints:
  - POST /               → advanced search
  - GET  /autocomplete    → fast autocomplete
  - GET  /facets          → search facets
  - GET  /did-you-mean    → typo correction (4.4)
  - GET  /geo             → geo proximity search (4.6)
  - POST /saved           → save a search (4.5)
  - GET  /saved           → list saved searches (4.5)
  - DELETE /saved/{id}    → delete saved search (4.5)
"""
from __future__ import annotations

from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select, func, and_, or_, text, cast, String, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Company, FinancialData, RiskScore, CompanyPerson
from app.schemas.schemas import SearchRequest, CompanyBrief, PaginatedResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.post("", response_model=PaginatedResponse)
async def advanced_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Advanced search with 50+ filters.
    """
    query = select(Company)
    count_query = select(func.count(Company.id))

    filters = []

    # ── Text search ──
    if body.query:
        q = body.query.strip()
        # If query is purely numeric, search by CUI exact match OR denumire
        if q.isdigit():
            filters.append(or_(
                Company.cui == int(q),
                Company.denumire.ilike(f"%{q}%"),
            ))
        else:
            filters.append(or_(
                Company.denumire.ilike(f"%{q}%"),
                cast(Company.cui, String).ilike(f"%{q}%"),
            ))

    # ── Geography filters ──
    if body.judet:
        filters.append(Company.judet == body.judet)

    if body.localitate:
        filters.append(Company.localitate.ilike(f"%{body.localitate}%"))

    if body.cod_postal:
        filters.append(Company.cod_postal == body.cod_postal)

    # ── Industry filters ──
    if body.caen_principal:
        if len(body.caen_principal) == 1:
            filters.append(Company.caen_principal == body.caen_principal[0])
        else:
            filters.append(Company.caen_principal.in_(body.caen_principal))

    if body.forma_juridica:
        if len(body.forma_juridica) == 1:
            filters.append(Company.forma_juridica == body.forma_juridica[0])
        else:
            filters.append(Company.forma_juridica.in_(body.forma_juridica))

    # ── Status filters ──
    if body.stare_firma:
        if len(body.stare_firma) == 1:
            filters.append(Company.stare == body.stare_firma[0])
        else:
            filters.append(Company.stare.in_(body.stare_firma))

    if body.platitor_tva is not None:
        filters.append(Company.platitor_tva == body.platitor_tva)

    if body.are_insolventa is not None:
        filters.append(Company.has_insolvency == body.are_insolventa)

    if body.are_datorii_stat is not None:
        filters.append(Company.has_debts == body.are_datorii_stat)

    if body.are_procese is not None:
        filters.append(Company.has_litigation == body.are_procese)

    if body.are_contracte_stat is not None:
        filters.append(Company.has_seap_contracts == body.are_contracte_stat)

    # ── Capital social filter ──
    if body.capital_social_min is not None:
        filters.append(Company.capital_social >= body.capital_social_min)

    # ── Date filters ──
    if body.data_infiintare_dupa:
        filters.append(Company.data_infiintare >= body.data_infiintare_dupa)
    if body.data_infiintare_inainte:
        filters.append(Company.data_infiintare <= body.data_infiintare_inainte)

    # ── Age filters ──
    if body.vechime_min_ani is not None:
        cutoff = date.today() - timedelta(days=body.vechime_min_ani * 365)
        filters.append(Company.data_infiintare <= cutoff)
    if body.vechime_max_ani is not None:
        cutoff = date.today() - timedelta(days=body.vechime_max_ani * 365)
        filters.append(Company.data_infiintare >= cutoff)

    # ── Financial filters (subquery join) ──
    if any([body.cifra_afaceri_min, body.cifra_afaceri_max,
            body.nr_angajati_min, body.nr_angajati_max,
            body.profit_net_min, body.are_profit,
            body.grad_indatorare_max]):

        fin_filters = []
        fin_query = select(FinancialData.company_id).distinct()

        if body.cifra_afaceri_min is not None:
            fin_filters.append(FinancialData.cifra_afaceri >= body.cifra_afaceri_min)
        if body.cifra_afaceri_max is not None:
            fin_filters.append(FinancialData.cifra_afaceri <= body.cifra_afaceri_max)
        if body.nr_angajati_min is not None:
            fin_filters.append(FinancialData.nr_angajati >= body.nr_angajati_min)
        if body.nr_angajati_max is not None:
            fin_filters.append(FinancialData.nr_angajati <= body.nr_angajati_max)
        if body.profit_net_min is not None:
            fin_filters.append(FinancialData.profit_net >= body.profit_net_min)
        if body.are_profit is True:
            fin_filters.append(FinancialData.profit_net > 0)
        if body.grad_indatorare_max is not None:
            fin_filters.append(FinancialData.grad_indatorare <= body.grad_indatorare_max)

        if fin_filters:
            fin_query = fin_query.where(and_(*fin_filters))
            filters.append(Company.id.in_(fin_query))

    # ── Risk score filter ──
    if body.scor_risc_max is not None:
        risk_subq = select(RiskScore.company_id).where(RiskScore.score <= body.scor_risc_max)
        filters.append(Company.id.in_(risk_subq))

    # ── Administrator filter ──
    if body.administrator:
        admin_subq = (
            select(CompanyPerson.company_id)
            .where(
                and_(
                    CompanyPerson.tip == "ADMINISTRATOR",
                    CompanyPerson.activ.is_(True),
                    CompanyPerson.nume_complet.ilike(f"%{body.administrator}%"),
                )
            )
        )
        filters.append(Company.id.in_(admin_subq))

    # ── Tara filter (all current data is Romania) ──
    if body.tara and body.tara.upper() not in ("ROMANIA", "RO", "ROM\u00c2NIA", ""):
        # No international companies yet — return empty result set
        filters.append(text("FALSE"))

    # Apply all filters
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # ── Sorting (4.3 fix: proper financial sort) ──
    sort_map = {
        "denumire": Company.denumire,
        "cui": Company.cui,
        "data_infiintare": Company.data_infiintare,
        "capital_social": Company.capital_social,
    }

    if body.sort_by == "cifra_afaceri":
        # Join financial data for revenue sorting
        latest_fin_sq = (
            select(
                FinancialData.company_id,
                func.max(FinancialData.an_fiscal).label("max_year"),
            )
            .group_by(FinancialData.company_id)
            .subquery()
        )
        fin_sq = (
            select(FinancialData.company_id, FinancialData.cifra_afaceri)
            .join(latest_fin_sq, and_(
                FinancialData.company_id == latest_fin_sq.c.company_id,
                FinancialData.an_fiscal == latest_fin_sq.c.max_year,
            ))
            .subquery()
        )
        query = query.outerjoin(fin_sq, Company.id == fin_sq.c.company_id)
        sort_col = fin_sq.c.cifra_afaceri
    elif body.sort_by == "risk_score":
        # Sort by RiskScore.score via outer join
        risk_sq = select(RiskScore.company_id, RiskScore.score).subquery()
        query = query.outerjoin(risk_sq, Company.id == risk_sq.c.company_id)
        sort_col = risk_sq.c.score
    else:
        sort_col = sort_map.get(body.sort_by, Company.id)

    if body.sort_dir == "ASC":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # ── Pagination ──
    page = body.page
    per_page = body.per_page
    offset = (page - 1) * per_page

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(per_page).options(selectinload(Company.risk_score))
    result = await db.execute(query)
    companies = result.scalars().all()

    return PaginatedResponse(
        items=[CompanyBrief.model_validate(c) for c in companies],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Fast autocomplete by company name.
    """
    result = await db.execute(
        select(
            Company.cui,
            Company.denumire,
            Company.judet,
            Company.stare,
        )
        .where(Company.denumire.ilike(f"%{q}%"))
        .order_by(Company.denumire)
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "cui": r.cui,
            "denumire": r.denumire,
            "judet": r.judet,
            "stare": r.stare,
        }
        for r in rows
    ]


@router.get("/facets")
async def search_facets(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Return aggregated facets for search filters (judet, CAEN, stare).
    """
    base_filter = []
    if q:
        base_filter.append(Company.denumire.ilike(f"%{q}%"))

    # Judet facets
    judet_q = select(
        Company.judet, func.count().label("cnt")
    )
    if base_filter:
        judet_q = judet_q.where(and_(*base_filter))
    judet_q = judet_q.group_by(Company.judet).order_by(text("cnt DESC")).limit(42)

    # CAEN facets (top 20)
    caen_q = select(
        Company.caen_principal, func.count().label("cnt")
    )
    if base_filter:
        caen_q = caen_q.where(and_(*base_filter))
    caen_q = caen_q.group_by(Company.caen_principal).order_by(text("cnt DESC")).limit(20)

    # Stare facets
    stare_q = select(
        Company.stare, func.count().label("cnt")
    )
    if base_filter:
        stare_q = stare_q.where(and_(*base_filter))
    stare_q = stare_q.group_by(Company.stare).order_by(text("cnt DESC"))

    judet_result = await db.execute(judet_q)
    caen_result = await db.execute(caen_q)
    stare_result = await db.execute(stare_q)

    return {
        "judete": [{"value": r.judet, "count": r.cnt} for r in judet_result.all()],
        "caen_codes": [{"value": r.caen_principal, "count": r.cnt} for r in caen_result.all()],
        "stari": [{"value": r.stare, "count": r.cnt} for r in stare_result.all()],
    }


# ──────────────────────────────────────────────────────────────────
# 4.4: Did You Mean
# ──────────────────────────────────────────────────────────────────

@router.get("/did-you-mean")
async def did_you_mean(
    q: str = Query(min_length=3, max_length=100),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    4.4: Suggest corrected query using trigram similarity.
    """
    service = SearchService(db=db)
    suggestion = await service.did_you_mean(q)
    return {"query": q, "suggestion": suggestion}


# ──────────────────────────────────────────────────────────────────
# 4.5: Saved Searches
# ──────────────────────────────────────────────────────────────────

@router.post("/saved")
async def save_search(
    name: str = Body(...),
    filters: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """4.5: Save a search for the current user."""
    service = SearchService(db=db)
    result = await service.save_search(user_id=user.sub, name=name, filters=filters)
    await db.commit()
    return result


@router.get("/saved")
async def list_saved_searches(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """4.5: List saved searches for the current user."""
    service = SearchService(db=db)
    return await service.get_saved_searches(user_id=user.sub)


@router.delete("/saved/{search_id}")
async def delete_saved_search(
    search_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """4.5: Delete a saved search."""
    service = SearchService(db=db)
    deleted = await service.delete_saved_search(user_id=user.sub, search_id=search_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    await db.commit()
    return {"deleted": True}


# ──────────────────────────────────────────────────────────────────
# 4.6: Geo Search
# ──────────────────────────────────────────────────────────────────

@router.get("/geo")
async def geo_search(
    judet: str = Query(..., description="County name (e.g., BUCURESTI, CLUJ)"),
    radius_km: float = Query(default=100, le=500),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    4.6: Find nearby counties with company counts, sorted by distance.
    """
    service = SearchService(db=db)
    results = await service.geo_search(judet=judet, radius_km=radius_km, limit=limit)
    if not results:
        raise HTTPException(status_code=404, detail="County not found")
    return {"center": judet.upper(), "radius_km": radius_km, "nearby": results}
