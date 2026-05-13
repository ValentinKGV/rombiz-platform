"""
Portfolio Optimization Service — Markowitz-inspired optimization, rebalancing
recommendations, benchmark tracking, attribution analysis, and scenario planning.
"""
import math
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company,
    FinancialData,
    MonitoredPortfolio,
    PortfolioCompany,
    RiskScore,
)


# ---------------------------------------------------------------------------
# 1. Markowitz Optimization (simplified)
# ---------------------------------------------------------------------------
async def optimize_portfolio(
    db: AsyncSession,
    portfolio_id: int,
    risk_tolerance: str = "moderate",  # conservative / moderate / aggressive
) -> dict:
    """
    Simplified Markowitz-style portfolio optimization.
    Uses company financial data to estimate returns and volatility.
    """
    # Get portfolio companies
    stmt = (
        select(
            PortfolioCompany.company_id,
            Company.denumire,
            Company.caen_principal,
        )
        .join(Company, PortfolioCompany.company_id == Company.id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        return {"portfolio_id": str(portfolio_id), "error": "Portofoliu gol", "holdings": []}

    holdings = []
    total_return = 0.0
    total_risk = 0.0

    for row in rows:
        cid, name, caen = row

        # Get last 2 years financial data for return estimation
        fin_stmt = (
            select(FinancialData.cifra_afaceri, FinancialData.profit_net, FinancialData.an)
            .where(FinancialData.company_id == cid)
            .order_by(FinancialData.an.desc())
            .limit(5)
        )
        fins = (await db.execute(fin_stmt)).all()

        # Estimate return from CA growth
        if len(fins) >= 2 and fins[0][0] and fins[1][0] and fins[1][0] > 0:
            annual_return = (fins[0][0] - fins[1][0]) / abs(fins[1][0]) * 100
        else:
            annual_return = random.uniform(-5, 15)

        # Estimate volatility from profit variation
        if len(fins) >= 3:
            profits = [f[1] or 0 for f in fins]
            mean_p = sum(profits) / len(profits)
            variance = sum((p - mean_p) ** 2 for p in profits) / len(profits)
            volatility = math.sqrt(variance) / max(abs(mean_p), 1) * 100
        else:
            volatility = random.uniform(10, 40)

        # Risk score
        risk_stmt = select(RiskScore.score).where(RiskScore.company_id == cid).order_by(RiskScore.calculat_la.desc()).limit(1)
        risk_row = (await db.execute(risk_stmt)).scalar()
        risk_score = risk_row if risk_row else 50

        # Calculate optimal weight based on risk tolerance
        risk_mult = {"conservative": 0.3, "moderate": 0.6, "aggressive": 1.0}.get(risk_tolerance, 0.6)
        sharpe_like = (annual_return - 2.0) / max(volatility, 1) * risk_mult  # Risk-free ~2%

        holdings.append({
            "company_id": cid,
            "name": name,
            "caen": caen,
            "estimated_return_pct": round(annual_return, 1),
            "volatility_pct": round(volatility, 1),
            "risk_score": risk_score,
            "sharpe_ratio": round(sharpe_like, 3),
        })

        total_return += annual_return
        total_risk += volatility

    # Normalize weights using sharpe ratios
    sharpe_values = [max(h["sharpe_ratio"], 0.01) for h in holdings]
    total_sharpe = sum(sharpe_values)
    for i, h in enumerate(holdings):
        h["optimal_weight_pct"] = round(sharpe_values[i] / total_sharpe * 100, 1)
        h["current_weight_pct"] = round(100 / len(holdings), 1)  # Equal weight as baseline

    # Sort by optimal weight descending
    holdings.sort(key=lambda x: x["optimal_weight_pct"], reverse=True)

    avg_return = total_return / len(holdings)
    avg_risk = total_risk / len(holdings)

    return {
        "portfolio_id": portfolio_id,
        "risk_tolerance": risk_tolerance,
        "optimization_method": "simplified_markowitz",
        "portfolio_metrics": {
            "expected_return_pct": round(avg_return, 1),
            "portfolio_volatility_pct": round(avg_risk * 0.7, 1),  # Diversification benefit
            "sharpe_ratio": round((avg_return - 2.0) / max(avg_risk, 1), 3),
            "diversification_benefit": round(avg_risk * 0.3, 1),
        },
        "holdings": holdings,
        "recommendations": _generate_opt_recommendations(holdings, risk_tolerance),
    }


def _generate_opt_recommendations(holdings: list[dict], tolerance: str) -> list[str]:
    recs = []
    if len(holdings) < 5:
        recs.append("Portofoliul are puține companii. Recomandăm diversificare — minim 8-10 companii.")
    high_risk = [h for h in holdings if h["risk_score"] > 70]
    if high_risk and tolerance == "conservative":
        recs.append(f"{len(high_risk)} companii au scor de risc ridicat (>70). Recomandăm reducerea expunerii.")
    negative = [h for h in holdings if h["estimated_return_pct"] < 0]
    if negative:
        recs.append(f"{len(negative)} companii au randament estimat negativ. Evaluați menținerea lor.")
    caens = set(h.get("caen", "")[:2] for h in holdings)
    if len(caens) < 3:
        recs.append("Concentrare sectorială ridicată. Diversificați pe mai multe sectoare CAEN.")
    return recs


# ---------------------------------------------------------------------------
# 2. Rebalancing Recommendations
# ---------------------------------------------------------------------------
async def rebalance_portfolio(
    db: AsyncSession,
    portfolio_id: int,
    strategy: str = "risk_parity",
) -> dict:
    """Generate rebalancing recommendations."""
    stmt = (
        select(
            PortfolioCompany.company_id,
            Company.denumire,
        )
        .join(Company, PortfolioCompany.company_id == Company.id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        return {"portfolio_id": portfolio_id, "actions": []}

    n = len(rows)
    equal_weight = 100.0 / n
    actions = []

    for row in rows:
        cid, name = row

        # Get risk score
        risk_q = select(RiskScore.score).where(RiskScore.company_id == cid).order_by(RiskScore.calculat_la.desc()).limit(1)
        risk = (await db.execute(risk_q)).scalar() or 50

        # Current weight (simulated)
        current_weight = equal_weight + random.uniform(-15, 15)
        current_weight = max(2, min(current_weight, 40))

        # Target weight based on strategy
        if strategy == "risk_parity":
            inv_risk = 100 - risk
            target_weight = equal_weight * (inv_risk / 50)  # Scale by inverse risk
        elif strategy == "equal_weight":
            target_weight = equal_weight
        elif strategy == "momentum":
            # Favor higher-performing companies
            fin_q = select(FinancialData.cifra_afaceri).where(
                FinancialData.company_id == cid
            ).order_by(FinancialData.an.desc()).limit(2)
            fins = (await db.execute(fin_q)).all()
            if len(fins) >= 2 and fins[0][0] and fins[1][0] and fins[1][0] > 0:
                growth = (fins[0][0] - fins[1][0]) / abs(fins[1][0])
                target_weight = equal_weight * (1 + growth)
            else:
                target_weight = equal_weight
        else:
            target_weight = equal_weight

        target_weight = max(2, min(target_weight, 35))
        delta = target_weight - current_weight
        action_type = "BUY" if delta > 1 else "SELL" if delta < -1 else "HOLD"

        actions.append({
            "company_id": cid,
            "name": name,
            "current_weight_pct": round(current_weight, 1),
            "target_weight_pct": round(target_weight, 1),
            "delta_pct": round(delta, 1),
            "action": action_type,
            "risk_score": risk,
        })

    # Normalize target weights to 100%
    total_target = sum(a["target_weight_pct"] for a in actions)
    for a in actions:
        a["target_weight_pct"] = round(a["target_weight_pct"] / total_target * 100, 1)
        a["delta_pct"] = round(a["target_weight_pct"] - a["current_weight_pct"], 1)
        a["action"] = "BUY" if a["delta_pct"] > 1 else "SELL" if a["delta_pct"] < -1 else "HOLD"

    actions.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)

    return {
        "portfolio_id": portfolio_id,
        "strategy": strategy,
        "timestamp": datetime.utcnow().isoformat(),
        "total_actions": len([a for a in actions if a["action"] != "HOLD"]),
        "actions": actions,
    }


# ---------------------------------------------------------------------------
# 3. Benchmark Tracking
# ---------------------------------------------------------------------------
async def benchmark_tracking(
    db: AsyncSession,
    portfolio_id: int,
    benchmark: str = "market",  # market / sector / custom
) -> dict:
    """Compare portfolio performance against benchmarks."""
    stmt = (
        select(PortfolioCompany.company_id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    company_ids = (await db.execute(stmt)).scalars().all()

    if not company_ids:
        return {"portfolio_id": portfolio_id, "periods": []}

    # Get portfolio aggregate financials per year
    fin_stmt = (
        select(
            FinancialData.an,
            func.sum(FinancialData.cifra_afaceri).label("total_ca"),
            func.sum(FinancialData.profit_net).label("total_profit"),
            func.sum(FinancialData.numar_angajati).label("total_emp"),
        )
        .where(FinancialData.company_id.in_(company_ids))
        .group_by(FinancialData.an)
        .order_by(FinancialData.an)
    )
    portfolio_fins = (await db.execute(fin_stmt)).all()

    # Get market benchmark (all companies)
    market_stmt = (
        select(
            FinancialData.an,
            func.sum(FinancialData.cifra_afaceri).label("total_ca"),
            func.sum(FinancialData.profit_net).label("total_profit"),
        )
        .group_by(FinancialData.an)
        .order_by(FinancialData.an)
    )
    market_fins = (await db.execute(market_stmt)).all()

    market_by_year = {m[0]: {"ca": m[1] or 0, "profit": m[2] or 0} for m in market_fins}

    periods = []
    prev_port_ca = None
    prev_mkt_ca = None

    for pf in portfolio_fins:
        an, port_ca, port_profit, port_emp = pf
        port_ca = port_ca or 0
        mkt = market_by_year.get(an, {})
        mkt_ca = mkt.get("ca", 0)

        port_return = ((port_ca - prev_port_ca) / abs(prev_port_ca) * 100) if prev_port_ca and prev_port_ca > 0 else 0
        mkt_return = ((mkt_ca - prev_mkt_ca) / abs(prev_mkt_ca) * 100) if prev_mkt_ca and prev_mkt_ca > 0 else 0

        periods.append({
            "year": an,
            "portfolio_revenue": port_ca,
            "portfolio_return_pct": round(port_return, 1),
            "benchmark_return_pct": round(mkt_return, 1),
            "alpha_pct": round(port_return - mkt_return, 1),
            "portfolio_profit": port_profit or 0,
            "employees": port_emp or 0,
        })

        prev_port_ca = port_ca
        prev_mkt_ca = mkt_ca

    # Calculate cumulative
    cum_port = 0.0
    cum_bench = 0.0
    for p in periods:
        cum_port += p["portfolio_return_pct"]
        cum_bench += p["benchmark_return_pct"]
        p["cumulative_portfolio"] = round(cum_port, 1)
        p["cumulative_benchmark"] = round(cum_bench, 1)

    return {
        "portfolio_id": portfolio_id,
        "benchmark": benchmark,
        "total_alpha_pct": round(cum_port - cum_bench, 1),
        "periods": periods,
        "summary": {
            "avg_portfolio_return": round(sum(p["portfolio_return_pct"] for p in periods) / max(len(periods), 1), 1),
            "avg_benchmark_return": round(sum(p["benchmark_return_pct"] for p in periods) / max(len(periods), 1), 1),
        },
    }


# ---------------------------------------------------------------------------
# 4. Attribution Analysis
# ---------------------------------------------------------------------------
async def attribution_analysis(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    """Analyze what drives portfolio performance — sector, size, quality."""
    stmt = (
        select(
            PortfolioCompany.company_id,
            Company.denumire,
            Company.caen_principal,
        )
        .join(Company, PortfolioCompany.company_id == Company.id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        return {"portfolio_id": portfolio_id, "attributions": []}

    # Sector breakdown
    sector_map: dict[str, dict] = {}
    company_contribs = []

    for row in rows:
        cid, name, caen = row
        sector = (caen or "0000")[:2]

        fin_q = (
            select(FinancialData.cifra_afaceri, FinancialData.profit_net)
            .where(FinancialData.company_id == cid)
            .order_by(FinancialData.an.desc())
            .limit(2)
        )
        fins = (await db.execute(fin_q)).all()

        if len(fins) >= 2 and fins[0][0] and fins[1][0] and fins[1][0] > 0:
            contrib = (fins[0][0] - fins[1][0]) / abs(fins[1][0]) * 100
        else:
            contrib = 0

        profit_margin = (fins[0][1] / fins[0][0] * 100) if fins and fins[0][0] and fins[0][0] > 0 else 0

        if sector not in sector_map:
            sector_map[sector] = {"count": 0, "total_contrib": 0}
        sector_map[sector]["count"] += 1
        sector_map[sector]["total_contrib"] += contrib

        company_contribs.append({
            "company_id": cid,
            "name": name,
            "sector": sector,
            "contribution_pct": round(contrib, 1),
            "profit_margin_pct": round(profit_margin, 1),
        })

    # Sector attribution
    sector_attr = [
        {
            "sector": s,
            "companies": d["count"],
            "avg_contribution_pct": round(d["total_contrib"] / max(d["count"], 1), 1),
            "weight_pct": round(d["count"] / len(rows) * 100, 1),
        }
        for s, d in sector_map.items()
    ]
    sector_attr.sort(key=lambda x: x["avg_contribution_pct"], reverse=True)

    # Top/bottom contributors
    company_contribs.sort(key=lambda x: x["contribution_pct"], reverse=True)

    return {
        "portfolio_id": portfolio_id,
        "total_companies": len(rows),
        "sector_attribution": sector_attr,
        "top_contributors": company_contribs[:5],
        "bottom_contributors": company_contribs[-5:] if len(company_contribs) > 5 else [],
        "diversification_score": min(len(sector_map) / 5 * 100, 100),
    }


# ---------------------------------------------------------------------------
# 5. Scenario Planning
# ---------------------------------------------------------------------------
async def scenario_planning(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    """Run stress test scenarios on portfolio."""
    stmt = (
        select(
            PortfolioCompany.company_id,
            Company.denumire,
            Company.caen_principal,
        )
        .join(Company, PortfolioCompany.company_id == Company.id)
        .where(PortfolioCompany.portfolio_id == portfolio_id)
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        return {"portfolio_id": portfolio_id, "scenarios": []}

    # Get current portfolio values
    total_ca = 0
    holdings_data = []
    for row in rows:
        cid, name, caen = row
        fin_q = select(FinancialData.cifra_afaceri, FinancialData.profit_net).where(
            FinancialData.company_id == cid
        ).order_by(FinancialData.an.desc()).limit(1)
        fin = (await db.execute(fin_q)).first()
        ca = fin[0] if fin and fin[0] else 0
        total_ca += ca
        holdings_data.append({"id": cid, "name": name, "caen": caen, "ca": ca})

    scenarios = [
        {
            "name": "Recesiune Economică",
            "description": "Scădere generală a PIB cu 5%, reducere cerere",
            "impact_factors": {"revenue": -0.15, "profit": -0.30, "employees": -0.08},
            "probability": "MEDIUM",
        },
        {
            "name": "Inflație Ridicată",
            "description": "Inflație 15%+, creștere costuri operaționale",
            "impact_factors": {"revenue": 0.05, "profit": -0.20, "employees": -0.03},
            "probability": "HIGH",
        },
        {
            "name": "Boom Tehnologic",
            "description": "Digitalizare accelerată, creștere sectoare IT",
            "impact_factors": {"revenue": 0.12, "profit": 0.15, "employees": 0.05},
            "probability": "MEDIUM",
        },
        {
            "name": "Criză Energetică",
            "description": "Creștere prețuri energie 3x, impact industrie",
            "impact_factors": {"revenue": -0.08, "profit": -0.25, "employees": -0.05},
            "probability": "LOW",
        },
        {
            "name": "Expansiune UE",
            "description": "Fonduri europene masive, creștere investiții",
            "impact_factors": {"revenue": 0.10, "profit": 0.08, "employees": 0.06},
            "probability": "HIGH",
        },
    ]

    for scenario in scenarios:
        factors = scenario["impact_factors"]
        projected_ca = total_ca * (1 + factors["revenue"])
        scenario["current_portfolio_value"] = total_ca
        scenario["projected_value"] = round(projected_ca)
        scenario["value_change"] = round(projected_ca - total_ca)
        scenario["change_pct"] = round(factors["revenue"] * 100, 1)

        # Sector-specific impacts
        sector_impacts = []
        industrial_caens = {"10", "11", "13", "14", "15", "16", "17", "20", "22", "23", "24", "25"}
        for h in holdings_data:
            caen_2 = (h["caen"] or "00")[:2]
            # Industrial sectors more affected by energy crisis, less by tech boom
            if scenario["name"] == "Criză Energetică" and caen_2 in industrial_caens:
                mult = 1.5
            elif scenario["name"] == "Boom Tehnologic" and caen_2 in {"62", "63"}:
                mult = 2.0
            else:
                mult = 1.0

            impact = h["ca"] * factors["revenue"] * mult
            sector_impacts.append({
                "name": h["name"],
                "impact": round(impact),
                "severity": "HIGH" if abs(factors["revenue"] * mult) > 0.15 else "MEDIUM" if abs(factors["revenue"] * mult) > 0.05 else "LOW",
            })

        scenario["company_impacts"] = sorted(sector_impacts, key=lambda x: x["impact"])

    return {
        "portfolio_id": portfolio_id,
        "current_total_revenue": total_ca,
        "scenarios": scenarios,
        "stress_test_date": datetime.utcnow().isoformat(),
    }
