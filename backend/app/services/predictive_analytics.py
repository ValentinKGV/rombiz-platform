"""
Predictive Analytics & ML Pipeline — Branch 13.

Sub-modules:
  13.1  Financial Forecasting  — Linear regression on CA / profit / angajați
  13.2  Bankruptcy Probability  — Logistic model using Z-Score + debt + age + sector
  13.3  Risk Degradation Prediction — Trend detection on risk scores
  13.4  Sector Trends         — CAEN sector aggregation: growth, births, deaths
  13.5  Monte Carlo Portfolio  — 1000-scenario portfolio risk simulation
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, func, and_, case, text, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, RiskScore, CompanyDebt,
    InsolvencyCase, MonitoredPortfolio, PortfolioCompany,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# 13.1  FINANCIAL FORECASTING
# ═══════════════════════════════════════════════════════════════════════

async def forecast_financials(
    db: AsyncSession,
    company_id: int,
    years_ahead: int = 3,
) -> dict:
    """
    Simple linear regression on historical financials to project
    cifra_afaceri, profit_net, nr_angajati for 1..years_ahead years.

    Returns dict with historical data + predictions + confidence.
    """
    stmt = (
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if len(rows) < 2:
        return {
            "company_id": company_id,
            "error": "Insuficiente date financiare (minim 2 ani)",
            "historical": [],
            "predictions": [],
        }

    # Build time series
    metrics = {
        "cifra_afaceri": [],
        "profit_net": [],
        "nr_angajati": [],
        "total_active": [],
        "total_datorii": [],
    }
    years: list[int] = []
    historical = []

    for row in rows:
        years.append(row.an_fiscal)
        historical.append({
            "an": row.an_fiscal,
            "cifra_afaceri": row.cifra_afaceri,
            "profit_net": row.profit_net,
            "nr_angajati": row.nr_angajati,
            "total_active": row.total_active,
            "total_datorii": row.total_datorii,
        })
        for key in metrics:
            val = getattr(row, key, None)
            metrics[key].append(float(val) if val is not None else None)

    last_year = max(years)
    predictions = []

    for y in range(1, years_ahead + 1):
        target_year = last_year + y
        pred: dict = {"an": target_year}

        for metric_name, values in metrics.items():
            # Filter out None values for regression
            valid = [(yr, v) for yr, v in zip(years, values) if v is not None]
            if len(valid) < 2:
                pred[metric_name] = None
                pred[f"{metric_name}_confidence"] = 0
                continue

            slope, intercept, r_squared = _linear_regression(
                [float(yr) for yr, _ in valid],
                [v for _, v in valid],
            )
            projected = slope * target_year + intercept
            # Employees can't be negative
            if metric_name == "nr_angajati":
                projected = max(0, projected)

            pred[metric_name] = round(projected)
            pred[f"{metric_name}_confidence"] = round(r_squared, 4)

        # Compute derived ratios
        if pred.get("cifra_afaceri") and pred.get("profit_net"):
            ca = pred["cifra_afaceri"]
            if ca != 0:
                pred["profit_margin_projected"] = round(pred["profit_net"] / ca, 4)
        if pred.get("total_active") and pred.get("total_datorii"):
            ta = pred["total_active"]
            if ta != 0:
                pred["grad_indatorare_projected"] = round(pred["total_datorii"] / ta, 4)

        predictions.append(pred)

    # Overall trend assessment
    ca_values = [v for v in metrics["cifra_afaceri"] if v is not None]
    trend = "STABIL"
    if len(ca_values) >= 2:
        slope, _, _ = _linear_regression(
            list(range(len(ca_values))), ca_values
        )
        avg_ca = sum(ca_values) / len(ca_values)
        if avg_ca > 0:
            growth_rate = slope / avg_ca
            if growth_rate > 0.05:
                trend = "CRESTERE"
            elif growth_rate < -0.05:
                trend = "SCADERE"

    return {
        "company_id": company_id,
        "years_ahead": years_ahead,
        "data_points": len(rows),
        "trend": trend,
        "historical": historical,
        "predictions": predictions,
        "methodology": "Linear regression on annual balance sheet data",
        "disclaimer": (
            "Predicțiile sunt generate automat prin regresie liniară pe date istorice. "
            "Acuratețea depinde de consistența datelor financiare raportate. "
            "Nu constituie sfat financiar sau recomandare de investiții."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# 13.2  BANKRUPTCY PROBABILITY
# ═══════════════════════════════════════════════════════════════════════

async def predict_bankruptcy(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Logistic-style bankruptcy probability using:
      - Altman Z-Score components (from latest financials)
      - Outstanding debts
      - Company age
      - Insolvency history
      - Sector risk factor

    Output: probability 0.0-1.0 and risk factors.
    """
    # Fetch company
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    # Latest financials
    stmt = (
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    fin = result.scalar_one_or_none()

    # Debts
    debt_stmt = (
        select(func.sum(CompanyDebt.suma_restanta))
        .where(CompanyDebt.company_id == company_id)
    )
    debt_result = await db.execute(debt_stmt)
    total_debt = debt_result.scalar() or Decimal("0")

    # Insolvency count
    insolvency_stmt = (
        select(func.count())
        .select_from(InsolvencyCase)
        .where(InsolvencyCase.company_id == company_id)
    )
    insolvency_result = await db.execute(insolvency_stmt)
    insolvency_count = insolvency_result.scalar() or 0

    # Risk score
    risk_stmt = select(RiskScore).where(RiskScore.company_id == company_id)
    risk_result = await db.execute(risk_stmt)
    risk_score = risk_result.scalar_one_or_none()

    # ── Feature extraction ──
    features: dict[str, float] = {}
    risk_factors: list[dict] = []

    # F1: Altman Z-Score proxy
    z_score = 3.0  # neutral default
    if fin and fin.total_active and fin.total_active > 0:
        ta = float(fin.total_active)
        working_capital = ta - float(fin.total_datorii or 0)
        retained_earnings = float(fin.capitaluri_prop or 0)
        ebit = float(fin.profit_net or 0) * 1.3  # rough proxy
        equity = float(fin.capitaluri_prop or 0)
        sales = float(fin.cifra_afaceri or 0)

        z_score = (
            1.2 * (working_capital / ta)
            + 1.4 * (retained_earnings / ta)
            + 3.3 * (ebit / ta)
            + 0.6 * (equity / max(float(fin.total_datorii or 1), 1))
            + 1.0 * (sales / ta)
        )
    features["z_score"] = z_score

    if z_score < 1.1:
        risk_factors.append({"factor": "z_score_critic", "impact": "HIGH",
                             "detail": f"Altman Z-Score = {z_score:.2f} (< 1.1 = zonă critică)"})
    elif z_score < 2.6:
        risk_factors.append({"factor": "z_score_gri", "impact": "MEDIUM",
                             "detail": f"Altman Z-Score = {z_score:.2f} (1.1-2.6 = zona gri)"})

    # F2: Debt pressure
    debt_ratio = 0.0
    if fin and fin.cifra_afaceri and fin.cifra_afaceri > 0:
        debt_ratio = float(total_debt) / float(fin.cifra_afaceri)
    features["debt_ratio"] = debt_ratio
    if debt_ratio > 0.3:
        risk_factors.append({"factor": "datorii_restante_mari", "impact": "HIGH",
                             "detail": f"Datorii restante = {debt_ratio:.1%} din CA"})

    # F3: Company age
    age_years = 0
    if company.data_infiintare:
        age_years = (date.today() - company.data_infiintare).days / 365.25
    features["age_years"] = age_years
    if age_years < 3:
        risk_factors.append({"factor": "firma_tanara", "impact": "MEDIUM",
                             "detail": f"Vechime: {age_years:.1f} ani (< 3 ani = risc crescut)"})

    # F4: Insolvency history
    features["insolvency_count"] = float(insolvency_count)
    if insolvency_count > 0:
        risk_factors.append({"factor": "istoric_insolventa", "impact": "CRITICAL",
                             "detail": f"{insolvency_count} proceduri de insolvență în istoric"})

    # F5: Negative equity
    negative_equity = False
    if fin and fin.capitaluri_prop is not None and fin.capitaluri_prop < 0:
        negative_equity = True
        risk_factors.append({"factor": "capitaluri_negative", "impact": "HIGH",
                             "detail": "Capitaluri proprii negative"})
    features["negative_equity"] = 1.0 if negative_equity else 0.0

    # F6: Profitability trend
    profit_declining = False
    fin_stmt = (
        select(FinancialData.profit_net, FinancialData.an_fiscal)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(3)
    )
    fin_result = await db.execute(fin_stmt)
    recent_profits = fin_result.all()
    if len(recent_profits) >= 2:
        profits = [float(p.profit_net) for p in recent_profits if p.profit_net is not None]
        if len(profits) >= 2 and all(p < 0 for p in profits[:2]):
            profit_declining = True
            risk_factors.append({"factor": "pierderi_consecutive", "impact": "HIGH",
                                 "detail": "Pierderi în ultimii 2+ ani consecutiv"})
    features["profit_declining"] = 1.0 if profit_declining else 0.0

    # ── Logistic scoring ──
    # Weighted combination → sigmoid → probability
    raw_score = (
        -0.8 * min(z_score, 5.0)      # lower Z = higher risk
        + 2.0 * debt_ratio             # debt pressure
        - 0.05 * min(age_years, 30)    # older = safer
        + 3.0 * features["insolvency_count"]
        + 1.5 * features["negative_equity"]
        + 1.0 * features["profit_declining"]
    )

    probability = 1.0 / (1.0 + math.exp(-raw_score))
    probability = min(max(probability, 0.001), 0.999)

    # Categorize
    if probability > 0.7:
        category = "CRITIC"
    elif probability > 0.4:
        category = "RIDICAT"
    elif probability > 0.2:
        category = "MODERAT"
    else:
        category = "SCAZUT"

    return {
        "company_id": company_id,
        "probability": round(probability, 4),
        "category": category,
        "features": features,
        "risk_factors": risk_factors,
        "risk_factors_count": len(risk_factors),
        "risk_score_actual": risk_score.score if risk_score else None,
        "model_version": "bankruptcy_v1.0",
        "disclaimer": (
            "Probabilitatea de faliment este estimată algoritmic pe baza datelor publice disponibile. "
            "Nu constituie predicție certă și necesită interpretare profesională."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# 13.3  RISK DEGRADATION PREDICTION
# ═══════════════════════════════════════════════════════════════════════

async def predict_risk_degradation(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Analyze financial trends to predict if a company's risk score
    will degrade in the next 6-12 months.

    Uses:
      - Financial trajectory (3-year slope)
      - Debt accumulation speed
      - Sector comparison
    """
    # Fetch financial history
    stmt = (
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an_fiscal.asc())
    )
    result = await db.execute(stmt)
    financials = result.scalars().all()

    # Current risk
    risk_stmt = select(RiskScore).where(RiskScore.company_id == company_id)
    risk_result = await db.execute(risk_stmt)
    current_risk = risk_result.scalar_one_or_none()

    company = await db.get(Company, company_id)

    warnings: list[dict] = []
    degradation_signals = 0
    total_signals = 6

    # Signal 1: Declining revenue
    ca_values = [(f.an_fiscal, float(f.cifra_afaceri)) for f in financials
                 if f.cifra_afaceri is not None]
    if len(ca_values) >= 2:
        slope, _, r2 = _linear_regression(
            [y for y, _ in ca_values], [v for _, v in ca_values]
        )
        avg_ca = sum(v for _, v in ca_values) / len(ca_values)
        if avg_ca > 0 and slope / avg_ca < -0.05:
            degradation_signals += 1
            warnings.append({
                "signal": "revenue_declining",
                "severity": "HIGH",
                "detail": f"Cifra de afaceri în scădere ({slope / avg_ca:.1%}/an)",
            })

    # Signal 2: Shrinking profitability
    profit_margins = []
    for f in financials:
        if f.cifra_afaceri and f.profit_net and f.cifra_afaceri > 0:
            profit_margins.append((f.an_fiscal, float(f.profit_net) / float(f.cifra_afaceri)))
    if len(profit_margins) >= 2:
        slope, _, _ = _linear_regression(
            [y for y, _ in profit_margins], [v for _, v in profit_margins]
        )
        if slope < -0.02:
            degradation_signals += 1
            warnings.append({
                "signal": "margins_compressing",
                "severity": "MEDIUM",
                "detail": "Marja de profit în comprimare",
            })

    # Signal 3: Rising debt level
    debt_ratios = []
    for f in financials:
        if f.total_active and f.total_datorii and f.total_active > 0:
            debt_ratios.append((f.an_fiscal, float(f.total_datorii) / float(f.total_active)))
    if len(debt_ratios) >= 2:
        slope, _, _ = _linear_regression(
            [y for y, _ in debt_ratios], [v for _, v in debt_ratios]
        )
        if slope > 0.03:
            degradation_signals += 1
            warnings.append({
                "signal": "debt_rising",
                "severity": "HIGH",
                "detail": "Gradul de îndatorare în creștere accelerată",
            })

    # Signal 4: Employee reduction
    emp_values = [(f.an_fiscal, float(f.nr_angajati)) for f in financials
                  if f.nr_angajati is not None and f.nr_angajati > 0]
    if len(emp_values) >= 2:
        slope, _, _ = _linear_regression(
            [y for y, _ in emp_values], [v for _, v in emp_values]
        )
        avg_emp = sum(v for _, v in emp_values) / len(emp_values)
        if avg_emp > 0 and slope / avg_emp < -0.10:
            degradation_signals += 1
            warnings.append({
                "signal": "employees_shrinking",
                "severity": "MEDIUM",
                "detail": f"Reducere personal ({slope / avg_emp:.1%}/an)",
            })

    # Signal 5: Negative equity trend
    equity_values = [(f.an_fiscal, float(f.capitaluri_prop)) for f in financials
                     if f.capitaluri_prop is not None]
    if len(equity_values) >= 2:
        slope, _, _ = _linear_regression(
            [y for y, _ in equity_values], [v for _, v in equity_values]
        )
        last_equity = equity_values[-1][1]
        if last_equity <= 0 or (last_equity > 0 and slope / last_equity < -0.15):
            degradation_signals += 1
            warnings.append({
                "signal": "equity_eroding",
                "severity": "CRITICAL",
                "detail": "Capitaluri proprii în erodare sau negative",
            })

    # Signal 6: Outstanding debts flag
    if company and company.has_debts:
        debt_sum_stmt = (
            select(func.sum(CompanyDebt.suma_restanta))
            .where(CompanyDebt.company_id == company_id)
        )
        debt_sum_result = await db.execute(debt_sum_stmt)
        total_debt = debt_sum_result.scalar() or 0
        if float(total_debt) > 0:
            degradation_signals += 1
            warnings.append({
                "signal": "outstanding_debts",
                "severity": "HIGH",
                "detail": f"Datorii restante la bugetul de stat: {float(total_debt):,.0f} RON",
            })

    # Calculate degradation probability
    degradation_prob = degradation_signals / total_signals
    if degradation_prob > 0.6:
        prediction = "DEGRADARE_PROBABILA"
    elif degradation_prob > 0.3:
        prediction = "RISC_MODERAT_DEGRADARE"
    else:
        prediction = "STABIL"

    # Predict future risk category
    current_score = current_risk.score if current_risk else 50
    projected_score = max(1, current_score - int(degradation_signals * 8))
    projected_rating = _score_to_rating(projected_score)

    return {
        "company_id": company_id,
        "current_score": current_score,
        "current_rating": current_risk.rating if current_risk else None,
        "projected_score_6m": projected_score,
        "projected_rating_6m": projected_rating,
        "degradation_probability": round(degradation_prob, 4),
        "prediction": prediction,
        "signals_detected": degradation_signals,
        "total_signals_checked": total_signals,
        "warnings": warnings,
        "disclaimer": (
            "Predicția degradării este bazată pe tendințe istorice și nu garantează "
            "rezultatul. Schimbările macroeconomice și decizionale pot altera traiectoria."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# 13.4  SECTOR TRENDS
# ═══════════════════════════════════════════════════════════════════════

async def analyze_sector_trends(
    db: AsyncSession,
    caen_code: str,
    years: int = 5,
) -> dict:
    """
    Aggregate sector-level trends for a given CAEN code (2-digit).
    Covers: company count, total CA, avg profit, employment, births/deaths.
    """
    caen_prefix = caen_code[:2]
    current_year = date.today().year
    start_year = current_year - years

    # Company count (active vs total)
    count_stmt = select(
        func.count(Company.id).label("total"),
        func.count(case(
            (Company.stare == "ACTIVA", Company.id),
        )).label("active"),
    ).where(Company.caen_principal.like(f"{caen_prefix}%"))
    count_result = await db.execute(count_stmt)
    counts = count_result.one()

    # Yearly financial aggregation
    yearly_stmt = (
        select(
            FinancialData.an_fiscal,
            func.count(FinancialData.id).label("companies_reporting"),
            func.sum(FinancialData.cifra_afaceri).label("total_ca"),
            func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
            func.sum(FinancialData.profit_net).label("total_profit"),
            func.avg(FinancialData.profit_net).label("avg_profit"),
            func.sum(FinancialData.nr_angajati).label("total_employees"),
            func.avg(FinancialData.nr_angajati).label("avg_employees"),
        )
        .join(Company, Company.id == FinancialData.company_id)
        .where(
            and_(
                Company.caen_principal.like(f"{caen_prefix}%"),
                FinancialData.an_fiscal >= start_year,
            )
        )
        .group_by(FinancialData.an_fiscal)
        .order_by(FinancialData.an_fiscal.asc())
    )
    yearly_result = await db.execute(yearly_stmt)
    yearly_rows = yearly_result.all()

    yearly_data = []
    for row in yearly_rows:
        yearly_data.append({
            "an": row.an_fiscal,
            "companies_reporting": row.companies_reporting,
            "total_ca": int(row.total_ca) if row.total_ca else 0,
            "avg_ca": round(float(row.avg_ca)) if row.avg_ca else 0,
            "total_profit": int(row.total_profit) if row.total_profit else 0,
            "avg_profit": round(float(row.avg_profit)) if row.avg_profit else 0,
            "total_employees": int(row.total_employees) if row.total_employees else 0,
            "avg_employees": round(float(row.avg_employees)) if row.avg_employees else 0,
        })

    # Company births (new registrations per year in this sector)
    births_stmt = (
        select(
            extract("year", Company.data_infiintare).label("year"),
            func.count(Company.id).label("count"),
        )
        .where(
            and_(
                Company.caen_principal.like(f"{caen_prefix}%"),
                Company.data_infiintare.isnot(None),
                extract("year", Company.data_infiintare) >= start_year,
            )
        )
        .group_by(extract("year", Company.data_infiintare))
        .order_by(text("year ASC"))
    )
    births_result = await db.execute(births_stmt)
    births = [{"an": int(r.year), "count": r.count} for r in births_result.all()]

    # Company deaths (radiated per year)
    deaths_stmt = (
        select(
            extract("year", Company.data_radiere).label("year"),
            func.count(Company.id).label("count"),
        )
        .where(
            and_(
                Company.caen_principal.like(f"{caen_prefix}%"),
                Company.data_radiere.isnot(None),
                extract("year", Company.data_radiere) >= start_year,
            )
        )
        .group_by(extract("year", Company.data_radiere))
        .order_by(text("year ASC"))
    )
    deaths_result = await db.execute(deaths_stmt)
    deaths = [{"an": int(r.year), "count": r.count} for r in deaths_result.all()]

    # Overall sector trend
    if len(yearly_data) >= 2:
        ca_trend_vals = [y["total_ca"] for y in yearly_data if y["total_ca"] > 0]
        if len(ca_trend_vals) >= 2:
            slope, _, _ = _linear_regression(
                list(range(len(ca_trend_vals))), [float(v) for v in ca_trend_vals]
            )
            avg_ca_total = sum(ca_trend_vals) / len(ca_trend_vals)
            growth_rate = slope / avg_ca_total if avg_ca_total > 0 else 0
            if growth_rate > 0.05:
                sector_trend = "CRESTERE"
            elif growth_rate < -0.05:
                sector_trend = "SCADERE"
            else:
                sector_trend = "STABIL"
        else:
            sector_trend = "INSUFICIENT_DATE"
    else:
        sector_trend = "INSUFICIENT_DATE"

    # Insolvency rate in sector
    insolvency_stmt = (
        select(func.count(Company.id))
        .where(
            and_(
                Company.caen_principal.like(f"{caen_prefix}%"),
                Company.has_insolvency.is_(True),
            )
        )
    )
    insolvency_result = await db.execute(insolvency_stmt)
    insolvency_count = insolvency_result.scalar() or 0
    insolvency_rate = insolvency_count / counts.total if counts.total > 0 else 0

    return {
        "caen_code": caen_prefix,
        "total_companies": counts.total,
        "active_companies": counts.active,
        "sector_trend": sector_trend,
        "insolvency_rate": round(insolvency_rate, 4),
        "yearly_data": yearly_data,
        "births": births,
        "deaths": deaths,
        "analysis_period": f"{start_year}-{current_year}",
    }


# ═══════════════════════════════════════════════════════════════════════
# 13.5  MONTE CARLO PORTFOLIO SIMULATION
# ═══════════════════════════════════════════════════════════════════════

async def monte_carlo_portfolio(
    db: AsyncSession,
    portfolio_id: str,
    simulations: int = 1000,
) -> dict:
    """
    Run Monte Carlo simulation on a portfolio to estimate:
      - Expected total revenue
      - Revenue at risk (VaR 95%)
      - Worst-case scenario
      - Default probability per company
    """
    # Get portfolio companies
    pc_stmt = (
        select(PortfolioCompany.company_id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    pc_result = await db.execute(pc_stmt)
    company_ids = [r.company_id for r in pc_result.all()]

    if not company_ids:
        return {
            "portfolio_id": portfolio_id,
            "error": "Portofoliul nu conține companii",
            "simulations": 0,
        }

    # Fetch latest financials and risk for each company
    companies_data = []
    for cid in company_ids:
        fin_stmt = (
            select(FinancialData)
            .where(FinancialData.company_id == cid)
            .order_by(FinancialData.an_fiscal.desc())
            .limit(2)
        )
        fin_result = await db.execute(fin_stmt)
        fins = fin_result.scalars().all()

        risk_stmt = select(RiskScore).where(RiskScore.company_id == cid)
        risk_result = await db.execute(risk_stmt)
        risk = risk_result.scalar_one_or_none()

        if not fins:
            continue

        latest = fins[0]
        ca = float(latest.cifra_afaceri or 0)
        profit = float(latest.profit_net or 0)

        # Compute volatility from history
        if len(fins) >= 2 and fins[1].cifra_afaceri and fins[1].cifra_afaceri > 0:
            ca_prev = float(fins[1].cifra_afaceri)
            volatility = abs(ca - ca_prev) / ca_prev
        else:
            volatility = 0.15  # default 15%

        # Default probability from risk score
        default_prob = 0.05  # default 5%
        if risk and risk.probabilitate_insolventa:
            default_prob = min(float(risk.probabilitate_insolventa), 0.95)
        elif risk:
            # Map score to probability
            default_prob = max(0.01, (100 - risk.score) / 200)

        companies_data.append({
            "company_id": cid,
            "ca": ca,
            "profit": profit,
            "volatility": min(volatility, 1.0),
            "default_prob": default_prob,
        })

    if not companies_data:
        return {
            "portfolio_id": portfolio_id,
            "error": "Niciuna din companii nu are date financiare",
            "simulations": 0,
        }

    # Run simulations
    random.seed(42)  # reproducibility
    simulation_results = []

    for _ in range(simulations):
        total_ca = 0.0
        total_profit = 0.0
        defaults = 0

        for comp in companies_data:
            # Check for default
            if random.random() < comp["default_prob"]:
                defaults += 1
                # Company defaults → partial recovery (30%)
                total_ca += comp["ca"] * 0.3
                total_profit += comp["profit"] * 0.1
            else:
                # Random shock based on volatility
                shock = random.gauss(1.0, comp["volatility"])
                shock = max(0.1, shock)  # floor at -90%
                total_ca += comp["ca"] * shock
                total_profit += comp["profit"] * shock

        simulation_results.append({
            "total_ca": total_ca,
            "total_profit": total_profit,
            "defaults": defaults,
        })

    # Statistics
    ca_results = sorted([s["total_ca"] for s in simulation_results])
    profit_results = sorted([s["total_profit"] for s in simulation_results])
    default_counts = [s["defaults"] for s in simulation_results]

    expected_ca = sum(ca_results) / len(ca_results)
    var_95_idx = int(len(ca_results) * 0.05)
    var_99_idx = int(len(ca_results) * 0.01)

    # Distribution buckets for chart
    min_ca = min(ca_results)
    max_ca = max(ca_results)
    bucket_count = 20
    bucket_size = (max_ca - min_ca) / bucket_count if max_ca > min_ca else 1
    distribution = []
    for i in range(bucket_count):
        low = min_ca + i * bucket_size
        high = low + bucket_size
        count = sum(1 for v in ca_results if low <= v < high)
        distribution.append({
            "range_low": round(low),
            "range_high": round(high),
            "count": count,
            "frequency": round(count / simulations, 4),
        })

    return {
        "portfolio_id": portfolio_id,
        "simulations": simulations,
        "companies_count": len(companies_data),
        "baseline_ca": round(sum(c["ca"] for c in companies_data)),
        "baseline_profit": round(sum(c["profit"] for c in companies_data)),
        "expected_ca": round(expected_ca),
        "expected_profit": round(sum(profit_results) / len(profit_results)),
        "var_95_ca": round(ca_results[var_95_idx]),
        "var_99_ca": round(ca_results[var_99_idx]),
        "worst_case_ca": round(min(ca_results)),
        "best_case_ca": round(max(ca_results)),
        "avg_defaults": round(sum(default_counts) / len(default_counts), 2),
        "max_defaults": max(default_counts),
        "distribution": distribution,
        "company_risks": [
            {
                "company_id": c["company_id"],
                "ca": round(c["ca"]),
                "default_prob": round(c["default_prob"], 4),
                "volatility": round(c["volatility"], 4),
            }
            for c in companies_data
        ],
        "disclaimer": (
            "Simularea Monte Carlo este un model probabilistic care generează scenarii ipotetice. "
            "Rezultatele nu sunt predicții și depind de calitatea datelor de intrare. "
            "Nu constituie sfat financiar sau recomandare de investiții."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _linear_regression(
    x: list[float], y: list[float]
) -> tuple[float, float, float]:
    """
    Simple linear regression: y = slope * x + intercept.
    Returns (slope, intercept, r_squared).
    """
    n = len(x)
    if n < 2:
        return 0.0, 0.0, 0.0

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_xx = sum(xi * xi for xi in x)
    sum_yy = sum(yi * yi for yi in y)

    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.0, sum_y / n if n > 0 else 0.0, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R-squared
    ss_tot = sum_yy - (sum_y * sum_y) / n
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    r_squared = max(0.0, min(1.0, r_squared))

    return slope, intercept, r_squared


def _score_to_rating(score: int) -> str:
    """Convert numeric risk score to letter rating."""
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 40:
        return "C"
    elif score >= 20:
        return "D"
    return "E"
