"""
International Expansion Service — cross-border company analysis, FX risk,
market entry scoring, regulatory comparison, and translation helpers.
"""
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company,
    FinancialData,
    RiskScore,
)


# ---------------------------------------------------------------------------
# Country / Market data
# ---------------------------------------------------------------------------
EU_COUNTRIES = {
    "RO": {"name": "România", "currency": "RON", "vat": 19, "corp_tax": 16, "population_m": 19.0, "gdp_b_eur": 285},
    "BG": {"name": "Bulgaria", "currency": "BGN", "vat": 20, "corp_tax": 10, "population_m": 6.5, "gdp_b_eur": 95},
    "HU": {"name": "Ungaria", "currency": "HUF", "vat": 27, "corp_tax": 9, "population_m": 9.7, "gdp_b_eur": 175},
    "PL": {"name": "Polonia", "currency": "PLN", "vat": 23, "corp_tax": 19, "population_m": 37.7, "gdp_b_eur": 655},
    "CZ": {"name": "Cehia", "currency": "CZK", "vat": 21, "corp_tax": 19, "population_m": 10.8, "gdp_b_eur": 280},
    "SK": {"name": "Slovacia", "currency": "EUR", "vat": 20, "corp_tax": 21, "population_m": 5.4, "gdp_b_eur": 115},
    "DE": {"name": "Germania", "currency": "EUR", "vat": 19, "corp_tax": 30, "population_m": 83.2, "gdp_b_eur": 4070},
    "FR": {"name": "Franța", "currency": "EUR", "vat": 20, "corp_tax": 25, "population_m": 67.8, "gdp_b_eur": 2780},
    "IT": {"name": "Italia", "currency": "EUR", "vat": 22, "corp_tax": 24, "population_m": 59.0, "gdp_b_eur": 2010},
    "AT": {"name": "Austria", "currency": "EUR", "vat": 20, "corp_tax": 25, "population_m": 9.1, "gdp_b_eur": 470},
    "MD": {"name": "Moldova", "currency": "MDL", "vat": 20, "corp_tax": 12, "population_m": 2.6, "gdp_b_eur": 15},
    "RS": {"name": "Serbia", "currency": "RSD", "vat": 20, "corp_tax": 15, "population_m": 6.6, "gdp_b_eur": 63},
}

FX_RATES = {
    "EUR/RON": 4.97, "USD/RON": 4.58, "GBP/RON": 5.82,
    "HUF/RON": 0.0127, "PLN/RON": 1.15, "CZK/RON": 0.198,
    "BGN/RON": 2.54, "MDL/RON": 0.257, "RSD/RON": 0.0425,
}


# ---------------------------------------------------------------------------
# 1. Cross-border Company Analysis
# ---------------------------------------------------------------------------
async def cross_border_analysis(
    db: AsyncSession,
    company_id: int,
    target_countries: list[str] | None = None,
) -> dict:
    """Analyze a Romanian company's cross-border expansion potential."""
    company = await db.get(Company, company_id)
    if not company:
        return {"company_id": company_id, "error": "Companie negăsită"}

    # Get financials
    fin_stmt = (
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an.desc())
        .limit(1)
    )
    fin = (await db.execute(fin_stmt)).scalar()

    ca = fin.cifra_afaceri if fin and fin.cifra_afaceri else 0
    profit = fin.profit_net if fin and fin.profit_net else 0
    employees = fin.numar_angajati if fin and fin.numar_angajati else 0

    targets = target_countries or ["BG", "HU", "PL", "DE", "MD"]
    country_analyses = []

    for code in targets:
        country = EU_COUNTRIES.get(code)
        if not country:
            continue

        # Market entry difficulty scoring
        tax_advantage = 16 - country["corp_tax"]  # vs Romania's 16%
        market_size_score = min(country["gdp_b_eur"] / 100, 10)  # 0-10 based on GDP

        # Entry barriers (simplified)
        entry_difficulty = 5  # base
        if country["currency"] != "EUR" and country["currency"] != "RON":
            entry_difficulty += 1  # FX risk
        if code in {"DE", "FR", "IT"}:
            entry_difficulty += 2  # Competition
        if code in {"MD", "RS"}:
            entry_difficulty -= 1  # Lower barriers

        # Revenue potential estimate
        revenue_potential = ca * (country["population_m"] / 19.0) * random.uniform(0.05, 0.15)

        country_analyses.append({
            "country_code": code,
            "country_name": country["name"],
            "currency": country["currency"],
            "vat_rate": country["vat"],
            "corporate_tax": country["corp_tax"],
            "tax_advantage_vs_ro": tax_advantage,
            "market_size_score": round(market_size_score, 1),
            "entry_difficulty": min(entry_difficulty, 10),
            "estimated_revenue_potential": round(revenue_potential),
            "population_millions": country["population_m"],
            "gdp_billions_eur": country["gdp_b_eur"],
            "recommendation": (
                "RECOMANDAT" if entry_difficulty <= 5 and market_size_score >= 3
                else "POSIBIL" if entry_difficulty <= 7
                else "DIFICIL"
            ),
        })

    country_analyses.sort(key=lambda x: x["market_size_score"] - x["entry_difficulty"], reverse=True)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "caen": company.caen_principal,
        "current_revenue": ca,
        "current_employees": employees,
        "target_markets": country_analyses,
        "best_market": country_analyses[0]["country_name"] if country_analyses else None,
    }


# ---------------------------------------------------------------------------
# 2. FX Risk Assessment
# ---------------------------------------------------------------------------
async def fx_risk_assessment(
    db: AsyncSession,
    company_id: int,
    exposure_currencies: list[str] | None = None,
) -> dict:
    """Assess foreign exchange risk for a company."""
    company = await db.get(Company, company_id)
    if not company:
        return {"company_id": company_id, "error": "Companie negăsită"}

    fin_stmt = (
        select(FinancialData.cifra_afaceri)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an.desc())
        .limit(1)
    )
    ca = (await db.execute(fin_stmt)).scalar() or 0

    currencies = exposure_currencies or ["EUR", "USD", "GBP"]
    exposures = []

    for curr in currencies:
        pair = f"{curr}/RON"
        rate = FX_RATES.get(pair, 1.0)

        # Simulate volatility (annual %)
        vol_map = {"EUR": 2.5, "USD": 8.0, "GBP": 7.5, "HUF": 5.0, "PLN": 6.0, "CZK": 4.5, "BGN": 0.5}
        volatility = vol_map.get(curr, 5.0)

        # Estimated exposure (% of revenue)
        exposure_pct = random.uniform(5, 40) if curr in {"EUR", "USD"} else random.uniform(2, 15)
        exposure_value = ca * exposure_pct / 100

        # VaR (Value at Risk) - simplified 95% confidence
        var_95 = exposure_value * volatility / 100 * 1.65  # 1.65σ for 95%

        exposures.append({
            "currency": curr,
            "pair": pair,
            "current_rate": rate,
            "annual_volatility_pct": volatility,
            "exposure_pct": round(exposure_pct, 1),
            "exposure_value_ron": round(exposure_value),
            "var_95_ron": round(var_95),
            "risk_level": "HIGH" if volatility > 6 else "MEDIUM" if volatility > 3 else "LOW",
            "hedging_recommendations": _fx_hedging_recs(curr, volatility, exposure_pct),
        })

    total_exposure = sum(e["exposure_value_ron"] for e in exposures)
    total_var = sum(e["var_95_ron"] for e in exposures)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "base_currency": "RON",
        "total_revenue": ca,
        "total_fx_exposure_ron": round(total_exposure),
        "total_var_95_ron": round(total_var),
        "overall_fx_risk": "HIGH" if total_var > ca * 0.05 else "MEDIUM" if total_var > ca * 0.02 else "LOW",
        "exposures": exposures,
    }


def _fx_hedging_recs(currency: str, volatility: float, exposure: float) -> list[str]:
    recs = []
    if volatility > 5:
        recs.append(f"Contract forward {currency}/RON pentru acoperirea riscului valutar")
    if exposure > 20:
        recs.append("Diversificarea portofoliului valutar pentru reducerea concentrării")
    if currency == "EUR":
        recs.append("Risc moderat — curs relativ stabil în ERM II")
    if volatility > 7:
        recs.append(f"Opțiuni put pe {currency}/RON ca asigurare împotriva deprecierii")
    return recs


# ---------------------------------------------------------------------------
# 3. Market Entry Scoring
# ---------------------------------------------------------------------------
async def market_entry_scoring(
    db: AsyncSession,
    caen_code: str,
    target_country: str = "DE",
) -> dict:
    """Score market entry viability for a sector in a target country."""
    country = EU_COUNTRIES.get(target_country, EU_COUNTRIES["DE"])

    # Count Romanian companies in this sector
    ro_count_q = select(func.count(Company.id)).where(
        Company.caen_principal.ilike(f"{caen_code[:2]}%"),
        Company.stare == "ACTIV",
    )
    ro_companies = (await db.execute(ro_count_q)).scalar() or 0

    # Financial benchmarks for sector in Romania
    fin_q = (
        select(
            func.avg(FinancialData.cifra_afaceri).label("avg_ca"),
            func.avg(FinancialData.profit_net).label("avg_profit"),
            func.avg(FinancialData.numar_angajati).label("avg_emp"),
        )
        .join(Company, FinancialData.company_id == Company.id)
        .where(
            Company.caen_principal.ilike(f"{caen_code[:2]}%"),
            FinancialData.an >= 2022,
        )
    )
    fin_data = (await db.execute(fin_q)).first()

    avg_ca = fin_data[0] if fin_data and fin_data[0] else 0
    avg_profit = fin_data[1] if fin_data and fin_data[1] else 0

    # Score components (0-100)
    market_size_score = min(country["gdp_b_eur"] / 50, 100)
    tax_score = max(0, (30 - country["corp_tax"]) / 30 * 100)
    competition_score = max(0, 100 - ro_companies / 10)  # fewer RO companies = less explored
    profitability_score = (avg_profit / max(avg_ca, 1) * 100 * 10) if avg_ca > 0 else 50

    overall = round(
        market_size_score * 0.3 +
        tax_score * 0.2 +
        min(competition_score, 100) * 0.2 +
        min(max(profitability_score, 0), 100) * 0.3,
        1
    )

    entry_steps = [
        {"step": 1, "action": "Studiu de piață", "duration": "2-4 săptămâni", "cost_eur": "2.000-5.000"},
        {"step": 2, "action": f"Înregistrare firmă în {country['name']}", "duration": "2-6 săptămâni", "cost_eur": "1.000-3.000"},
        {"step": 3, "action": "Obținere cod fiscal local", "duration": "1-3 săptămâni", "cost_eur": "500-1.500"},
        {"step": 4, "action": "Deschidere cont bancar", "duration": "1-2 săptămâni", "cost_eur": "200-500"},
        {"step": 5, "action": "Angajare personal local / partener", "duration": "4-8 săptămâni", "cost_eur": "5.000-15.000"},
        {"step": 6, "action": "Lansare operațiuni", "duration": "2-4 săptămâni", "cost_eur": "3.000-10.000"},
    ]

    return {
        "caen_code": caen_code,
        "target_country": target_country,
        "country_name": country["name"],
        "overall_score": overall,
        "verdict": "FAVORABIL" if overall >= 60 else "MODERAT" if overall >= 40 else "NEFAVORABIL",
        "score_breakdown": {
            "market_size": round(market_size_score, 1),
            "tax_efficiency": round(tax_score, 1),
            "competition": round(min(competition_score, 100), 1),
            "profitability": round(min(max(profitability_score, 0), 100), 1),
        },
        "ro_sector_stats": {
            "companies_count": ro_companies,
            "avg_revenue": round(avg_ca) if avg_ca else 0,
            "avg_profit": round(avg_profit) if avg_profit else 0,
        },
        "country_info": country,
        "entry_steps": entry_steps,
        "estimated_total_cost_eur": "12.000-35.000",
        "estimated_timeline": "3-6 luni",
    }


# ---------------------------------------------------------------------------
# 4. Regulatory Comparison
# ---------------------------------------------------------------------------
async def regulatory_comparison(
    db: AsyncSession,
    countries: list[str] | None = None,
) -> dict:
    """Compare regulatory environments across countries."""
    target = countries or ["RO", "BG", "HU", "PL", "DE"]

    comparisons = []
    for code in target:
        country = EU_COUNTRIES.get(code)
        if not country:
            continue

        # Ease of doing business scores (simplified)
        ease_scores = {
            "RO": 55, "BG": 61, "HU": 52, "PL": 76, "CZ": 73, "SK": 68,
            "DE": 79, "FR": 76, "IT": 58, "AT": 78, "MD": 48, "RS": 44,
        }

        reg_details = {
            "country_code": code,
            "country_name": country["name"],
            "ease_of_business_score": ease_scores.get(code, 50),
            "corporate_tax_pct": country["corp_tax"],
            "vat_rate_pct": country["vat"],
            "currency": country["currency"],
            "eu_member": code not in {"MD", "RS"},
            "eurozone": country["currency"] == "EUR",
            "labor_regulations": _labor_reg(code),
            "data_protection": "GDPR" if code not in {"MD", "RS"} else "Local",
            "company_registration_days": {"RO": 3, "BG": 4, "HU": 5, "PL": 7, "DE": 10, "FR": 7, "IT": 11, "CZ": 9, "SK": 6, "AT": 8, "MD": 5, "RS": 6}.get(code, 7),
            "minimum_capital_eur": {"RO": 45, "BG": 1, "HU": 2500, "PL": 1200, "DE": 25000, "FR": 1, "IT": 1, "CZ": 200, "SK": 5000, "AT": 35000, "MD": 10, "RS": 1}.get(code, 100),
            "double_tax_treaty_ro": code != "RS",
        }

        comparisons.append(reg_details)

    comparisons.sort(key=lambda x: x["ease_of_business_score"], reverse=True)

    return {
        "comparison_date": datetime.utcnow().isoformat(),
        "countries_compared": len(comparisons),
        "comparisons": comparisons,
        "best_tax_environment": min(comparisons, key=lambda x: x["corporate_tax_pct"])["country_name"] if comparisons else None,
        "easiest_business": comparisons[0]["country_name"] if comparisons else None,
    }


def _labor_reg(code: str) -> dict:
    data = {
        "RO": {"min_wage_eur": 620, "severance_weeks": 20, "max_hours_week": 48, "flexibility": "MEDIUM"},
        "BG": {"min_wage_eur": 400, "severance_weeks": 4, "max_hours_week": 48, "flexibility": "HIGH"},
        "HU": {"min_wage_eur": 580, "severance_weeks": 12, "max_hours_week": 48, "flexibility": "MEDIUM"},
        "PL": {"min_wage_eur": 840, "severance_weeks": 12, "max_hours_week": 48, "flexibility": "MEDIUM"},
        "DE": {"min_wage_eur": 2054, "severance_weeks": 24, "max_hours_week": 48, "flexibility": "LOW"},
        "FR": {"min_wage_eur": 1747, "severance_weeks": 24, "max_hours_week": 35, "flexibility": "LOW"},
        "IT": {"min_wage_eur": 0, "severance_weeks": 16, "max_hours_week": 40, "flexibility": "LOW"},
        "CZ": {"min_wage_eur": 700, "severance_weeks": 12, "max_hours_week": 40, "flexibility": "MEDIUM"},
        "SK": {"min_wage_eur": 700, "severance_weeks": 12, "max_hours_week": 48, "flexibility": "MEDIUM"},
        "AT": {"min_wage_eur": 1800, "severance_weeks": 24, "max_hours_week": 40, "flexibility": "LOW"},
        "MD": {"min_wage_eur": 180, "severance_weeks": 4, "max_hours_week": 40, "flexibility": "HIGH"},
        "RS": {"min_wage_eur": 400, "severance_weeks": 8, "max_hours_week": 40, "flexibility": "MEDIUM"},
    }
    return data.get(code, {"min_wage_eur": 0, "severance_weeks": 0, "max_hours_week": 40, "flexibility": "MEDIUM"})


# ---------------------------------------------------------------------------
# 5. Business Term Translation
# ---------------------------------------------------------------------------
async def translate_business_terms(
    db: AsyncSession,
    terms: list[str] | None = None,
    target_language: str = "en",
) -> dict:
    """Translate Romanian business/legal terms to other languages."""
    # Core business terms dictionary
    dictionary = {
        "ro_en": {
            "Cifra de afaceri": "Revenue / Turnover",
            "Profit net": "Net Profit",
            "Capital social": "Share Capital",
            "Societate cu Răspundere Limitată": "Limited Liability Company (LLC)",
            "Societate pe Acțiuni": "Joint Stock Company",
            "Cod Unic de Înregistrare": "Tax Identification Number (TIN)",
            "Registrul Comerțului": "Trade Register",
            "Numărul de Ordine în Registrul Comerțului": "Trade Register Number",
            "Bilanț contabil": "Balance Sheet",
            "Cont de profit și pierdere": "Profit & Loss Statement",
            "Impozit pe profit": "Corporate Income Tax",
            "TVA": "VAT (Value Added Tax)",
            "Fond de rulment": "Working Capital",
            "Creanțe": "Receivables",
            "Datorii": "Liabilities / Debts",
            "Active imobilizate": "Fixed Assets",
            "Active circulante": "Current Assets",
            "Stare: ACTIV": "Status: ACTIVE",
            "Insolvență": "Insolvency / Bankruptcy",
            "Lichidare": "Liquidation",
            "Administrator": "Director / Manager",
            "Asociat": "Shareholder / Partner",
            "Angajat": "Employee",
            "Cod CAEN": "NACE Code (Industry Classification)",
            "Certificat de înregistrare": "Certificate of Incorporation",
            "Act constitutiv": "Articles of Association",
            "Adunarea Generală a Asociaților": "General Assembly of Shareholders",
        },
        "ro_de": {
            "Cifra de afaceri": "Umsatz",
            "Profit net": "Nettogewinn",
            "Capital social": "Stammkapital",
            "Societate cu Răspundere Limitată": "Gesellschaft mit beschränkter Haftung (GmbH)",
            "Societate pe Acțiuni": "Aktiengesellschaft (AG)",
            "Cod Unic de Înregistrare": "Steueridentifikationsnummer",
            "Bilanț contabil": "Bilanz",
            "Impozit pe profit": "Körperschaftsteuer",
            "TVA": "MwSt (Mehrwertsteuer)",
            "Insolvență": "Insolvenz",
            "Administrator": "Geschäftsführer",
        },
        "ro_fr": {
            "Cifra de afaceri": "Chiffre d'affaires",
            "Profit net": "Bénéfice net",
            "Capital social": "Capital social",
            "Societate cu Răspundere Limitată": "Société à responsabilité limitée (SARL)",
            "Societate pe Acțiuni": "Société anonyme (SA)",
            "Bilanț contabil": "Bilan comptable",
            "Impozit pe profit": "Impôt sur les sociétés",
            "TVA": "TVA (Taxe sur la valeur ajoutée)",
            "Insolvență": "Insolvabilité",
            "Administrator": "Gérant / Directeur",
        },
    }

    dict_key = f"ro_{target_language}"
    available_dict = dictionary.get(dict_key, dictionary["ro_en"])

    if terms:
        translations = [
            {
                "term_ro": term,
                "translation": available_dict.get(term, f"[{term}]"),
                "found": term in available_dict,
            }
            for term in terms
        ]
    else:
        translations = [
            {"term_ro": k, "translation": v, "found": True}
            for k, v in available_dict.items()
        ]

    return {
        "source_language": "ro",
        "target_language": target_language,
        "available_languages": ["en", "de", "fr"],
        "total_terms": len(translations),
        "translations": translations,
        "coverage_pct": round(
            sum(1 for t in translations if t["found"]) / max(len(translations), 1) * 100, 1
        ),
    }
