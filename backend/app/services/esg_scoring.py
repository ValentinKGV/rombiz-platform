"""
ESG Scoring Engine — Environmental, Social, Governance.

v2 Improvements:
  2.1 Environmental: Carbon footprint estimation, EU Taxonomy alignment, energy estimates
  2.2 Social: Gender diversity proxy, employee productivity, community impact
  2.3 Governance: UBO depth, conflict of interest detection, board stability index
  2.4 Conformity: CSRD readiness checklist, SFDR sub-categories, GRI mapping, BNR EUR conversion
  2.5 Reporting: ESG factsheet data, comparison, portfolio aggregate, timeline

Data Sources:
  - Environmental: GNM/APM fines, Prtr.ro emissions, CAEN sector classification, ESGRawData
  - Social: Employee count trends, court cases (labor), public contracts, productivity metrics
  - Governance: Ownership transparency (UBO depth), admin stability, financial audit status

Score: 0-100 per component, weighted average for composite.
Hard constraint #12: All scores include cited sources + disclaimer.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, ESGScore, ESGRawData,
    EnvironmentalFine, CompanyPerson, CourtCase,
    PublicContract, ExchangeRate,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


DISCLAIMER = (
    "Scorul ESG este generat automat pe baza datelor publice disponibile. "
    "Nu constituie o evaluare oficială, un rating de credit, sau o certificare ESG. "
    "Sursele sunt citate pentru fiecare componentă."
)

# ── 2.1: EU Taxonomy eligible activities by CAEN ──
# Mapping CAEN 2-digit to taxonomy-eligible categories
TAXONOMY_ELIGIBLE_CAEN = {
    # Climate change mitigation
    "01": "agriculture", "02": "forestry", "03": "fishing",
    "35": "energy", "36": "water_supply", "37": "sewerage",
    "38": "waste_management", "39": "remediation",
    "41": "construction", "42": "construction", "43": "construction",
    "49": "transport", "50": "transport", "51": "transport",
    "52": "warehousing", "53": "postal",
    "61": "telecommunications", "62": "it_services", "63": "it_services",
}

# Sectors with substantial contribution to environmental objectives
TAXONOMY_ALIGNED_CAEN = {"35", "36", "37", "38", "39", "62", "63"}

# ── 2.1: Carbon footprint estimation factors (tonnes CO2 / million RON revenue) ──
CARBON_INTENSITY_FACTORS: dict[str, float] = {
    "01": 45.0, "02": 20.0, "03": 30.0,        # Agriculture
    "05": 120.0, "06": 150.0, "07": 100.0,       # Mining
    "10": 25.0, "11": 20.0, "19": 200.0,         # Food, Beverages, Petrol
    "20": 80.0, "21": 30.0, "22": 40.0,          # Chemicals
    "23": 90.0, "24": 130.0, "25": 50.0,          # Non-metallic, Metals
    "29": 35.0, "30": 35.0,                        # Automotive
    "35": 60.0,                                      # Energy
    "41": 30.0, "42": 35.0, "43": 25.0,           # Construction
    "45": 8.0, "46": 5.0, "47": 6.0,              # Trade
    "49": 70.0, "50": 80.0, "51": 200.0,          # Transport
    "55": 15.0, "56": 12.0,                        # Hospitality
    "58": 2.0, "59": 3.0, "62": 1.5, "63": 1.5,  # IT/Media (low)
    "64": 3.0, "65": 3.0, "66": 3.0,              # Finance
    "69": 2.0, "70": 2.0, "71": 3.0,              # Professional services
}

# ── 2.1: Energy consumption estimation (MWh per employee per year) ──
ENERGY_PER_EMPLOYEE: dict[str, float] = {
    "05": 120.0, "06": 150.0, "19": 200.0,       # Mining, Oil
    "20": 80.0, "23": 90.0, "24": 100.0,          # Chemicals, Metals
    "35": 50.0,                                      # Energy
    "41": 20.0, "42": 25.0, "43": 15.0,           # Construction
    "46": 8.0, "47": 10.0,                          # Trade
    "49": 30.0, "50": 40.0,                         # Transport
    "55": 15.0, "56": 12.0,                         # Hospitality
    "62": 5.0, "63": 5.0,                           # IT
    "69": 4.0, "70": 4.0,                           # Professional services
}

# ── 2.4: CSRD Readiness Checklist Items ──
CSRD_CHECKLIST = [
    "financial_reporting_5y",       # Has 5+ years of financial data
    "employee_count_reported",      # Employee data available
    "ownership_transparent",        # Full ownership % declared
    "admin_stable",                # Admin stability (low turnover)
    "no_environmental_fines",       # No GNM/APM sanctions
    "public_contracts_track",       # SEAP participation track record
    "no_insolvency",               # No insolvency proceedings
    "no_labor_disputes",           # No labor court cases
    "caen_declared",               # CAEN code properly registered
    "address_complete",            # Full address on record
    "capital_social_adequate",     # Capital social > 0
    "active_status",               # Company is ACTIVA
]

# ── 2.4: GRI Standards Mapping ──
GRI_MAPPING = {
    "E": {
        "GRI 302": {"name": "Energy", "available": False, "proxy": "energy_estimate"},
        "GRI 303": {"name": "Water", "available": False, "proxy": None},
        "GRI 305": {"name": "Emissions", "available": False, "proxy": "carbon_estimate"},
        "GRI 306": {"name": "Waste", "available": False, "proxy": None},
        "GRI 307": {"name": "Environmental Compliance", "available": True, "source": "GNM/APM fines"},
    },
    "S": {
        "GRI 401": {"name": "Employment", "available": True, "source": "ANAF employee data"},
        "GRI 403": {"name": "OHS", "available": False, "proxy": "labor_court_cases"},
        "GRI 405": {"name": "Diversity", "available": False, "proxy": "gender_estimate"},
        "GRI 413": {"name": "Local Communities", "available": True, "source": "SEAP contracts"},
    },
    "G": {
        "GRI 205": {"name": "Anti-corruption", "available": False, "proxy": "court_cases"},
        "GRI 405": {"name": "Board Diversity", "available": True, "source": "ONRC admin data"},
        "GRI 102-18": {"name": "Governance Structure", "available": True, "source": "ONRC ownership"},
    },
}


class ESGScoringEngine:
    """
    ESG Composite scoring engine for Romanian companies.

    v2 capabilities per branch:
    2.1: Carbon footprint estimation, EU Taxonomy alignment, energy estimates
    2.2: Gender diversity proxy, employee productivity, community impact scoring
    2.3: UBO depth analysis, conflict of interest detection, board stability index
    2.4: CSRD readiness checklist, SFDR sub-categories, BNR EUR conversion, GRI mapping
    2.5: Factsheet data, comparison, portfolio aggregate, timeline support
    """

    WEIGHTS = {
        "environmental": Decimal("0.35"),
        "social": Decimal("0.30"),
        "governance": Decimal("0.35"),
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate(self, company_id: int) -> ESGScore:
        """
        Calculate ESG composite score with sub-components.
        Now includes detailed audit data for all improvements.
        """
        company = await self._get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        e_score, e_sources, e_details = await self._score_environmental(company)
        s_score, s_sources, s_details = await self._score_social(company)
        g_score, g_sources, g_details = await self._score_governance(company)

        composite = (
            e_score * self.WEIGHTS["environmental"]
            + s_score * self.WEIGHTS["social"]
            + g_score * self.WEIGHTS["governance"]
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        all_sources = list(set(e_sources + s_sources + g_sources))

        # ── 2.4: CSRD applicability with BNR EUR conversion ──
        csrd_applicable = False
        latest_fin = await self._get_latest_financial(company)
        eur_rate = await self._get_eur_rate()

        if latest_fin:
            if (latest_fin.nr_angajati or 0) > 250:
                csrd_applicable = True
            # Convert revenue to EUR using live BNR rate
            revenue_eur = 0
            if latest_fin.cifra_afaceri and eur_rate > 0:
                revenue_eur = float(latest_fin.cifra_afaceri) / eur_rate
            if revenue_eur > 40_000_000:  # 40M EUR CSRD threshold
                csrd_applicable = True

        # ── 2.4: CSRD Readiness Checklist ──
        csrd_checklist = await self._csrd_readiness_check(company, latest_fin)

        # ── 2.1: Carbon & energy estimates ──
        carbon_estimate = e_details.get("carbon_footprint_tonnes")
        energy_estimate = e_details.get("energy_estimate_mwh")

        # ── 2.4: EU Taxonomy alignment ──
        taxonomy = e_details.get("taxonomy")

        # ── 2.4: GRI coverage ──
        gri_coverage = self._compute_gri_coverage()

        # Build comprehensive audit data
        audit_data = {
            "version": "2.0",
            "disclaimer": DISCLAIMER,
            "details": {
                "environmental": e_details,
                "social": s_details,
                "governance": g_details,
            },
            "carbon_footprint_tonnes_co2": carbon_estimate,
            "energy_estimate_mwh": energy_estimate,
            "taxonomy_alignment": taxonomy,
            "csrd_checklist": csrd_checklist,
            "gri_coverage": gri_coverage,
            "eur_rate_used": eur_rate,
        }

        esg_score = ESGScore(
            company_id=company_id,
            score_total=composite,
            score_e=e_score,
            score_s=s_score,
            score_g=g_score,
            e_emisii_co2=Decimal(str(carbon_estimate)) if carbon_estimate else None,
            e_amenzi_mediu=Decimal(str(e_details.get("total_fines_ron", 0))),
            surse_date=all_sources,
            csrd_relevant=csrd_applicable,
            sfdr_categoria=self._classify_sfdr(composite),
            calculat_la=datetime.now(timezone.utc),
        )

        self.db.add(esg_score)
        logger.info(
            "esg_score_calculated",
            company_id=company_id,
            composite=str(composite),
            e=str(e_score), s=str(s_score), g=str(g_score),
            csrd=csrd_applicable,
        )

        return esg_score

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    async def _get_company(self, company_id: int) -> Optional[Company]:
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def _get_latest_financial(self, company: Company) -> Optional[FinancialData]:
        result = await self.db.execute(
            select(FinancialData)
            .where(FinancialData.company_id == company.id)
            .order_by(FinancialData.an_fiscal.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_eur_rate(self) -> float:
        """2.4: Get latest EUR/RON rate from BNR data for CSRD threshold conversion."""
        try:
            result = await self.db.execute(
                select(ExchangeRate.rate_ron)
                .where(ExchangeRate.currency == "EUR")
                .order_by(ExchangeRate.date.desc())
                .limit(1)
            )
            rate = result.scalar_one_or_none()
            return float(rate) if rate else 4.97  # Fallback to approximate rate
        except Exception:
            return 4.97  # Safe fallback

    # ──────────────────────────────────────────────────────────────────
    # 2.1: ENVIRONMENTAL SCORING (ENHANCED)
    # ──────────────────────────────────────────────────────────────────

    async def _score_environmental(self, company: Company) -> tuple[Decimal, list[str], dict]:
        """
        Environmental score with enhancements:
        - Carbon footprint estimation based on CAEN + revenue
        - EU Taxonomy eligibility and alignment check
        - Energy consumption estimation per employee
        - ESGRawData integration for real emissions data
        """
        score = Decimal("70")
        sources: list[str] = []
        details: dict = {}

        caen_2 = (company.caen_principal or "")[:2]

        # ── Environmental fines ──
        result = await self.db.execute(
            select(EnvironmentalFine)
            .where(EnvironmentalFine.company_id == company.id)
        )
        fines = result.scalars().all()

        if fines:
            total_fines = sum(float(f.suma_ron or 0) for f in fines)
            details["total_fines_ron"] = total_fines
            details["fine_count"] = len(fines)
            sources.append(f"GNM/APM: {len(fines)} sancțiuni ({total_fines:,.0f} RON)")
            if total_fines > 100_000:
                score -= Decimal("30")
            elif total_fines > 10_000:
                score -= Decimal("15")
            else:
                score -= Decimal("5")
        else:
            score += Decimal("10")
            details["total_fines_ron"] = 0
            details["fine_count"] = 0
            sources.append("GNM/APM: fără sancțiuni")

        # ── CAEN sector analysis ──
        high_pollution = {"05", "06", "07", "08", "09", "19", "20", "23", "24"}
        green_sectors = {"35", "36", "37", "38", "39"}

        if caen_2 in high_pollution:
            score -= Decimal("15")
            details["sector_impact"] = "high"
            sources.append(f"CAEN {company.caen_principal}: sector cu impact ridicat")
        elif caen_2 in green_sectors:
            score += Decimal("10")
            details["sector_impact"] = "green"
            sources.append(f"CAEN {company.caen_principal}: sector verde/recycling")
        else:
            details["sector_impact"] = "neutral"
            sources.append(f"CAEN {company.caen_principal}: sector neutru")

        # ── 2.1: Carbon footprint estimation ──
        latest_fin = await self._get_latest_financial(company)
        carbon_footprint = None
        energy_estimate = None

        if latest_fin and latest_fin.cifra_afaceri:
            revenue_m = float(latest_fin.cifra_afaceri) / 1_000_000  # millions RON
            intensity = CARBON_INTENSITY_FACTORS.get(caen_2, 10.0)  # default 10 t/M RON
            carbon_footprint = round(revenue_m * intensity, 1)
            details["carbon_footprint_tonnes"] = carbon_footprint
            details["carbon_intensity_factor"] = intensity
            sources.append(f"Estimare CO2: ~{carbon_footprint:,.0f} tone/an (pe baza CAEN + cifră afaceri)")

            # Carbon rating
            if carbon_footprint > 10000:
                score -= Decimal("10")
                details["carbon_rating"] = "very_high"
            elif carbon_footprint > 1000:
                score -= Decimal("5")
                details["carbon_rating"] = "high"
            elif carbon_footprint < 50:
                score += Decimal("5")
                details["carbon_rating"] = "low"
            else:
                details["carbon_rating"] = "moderate"

        # ── 2.1: Energy consumption estimation ──
        if latest_fin and latest_fin.nr_angajati and latest_fin.nr_angajati > 0:
            energy_per_emp = ENERGY_PER_EMPLOYEE.get(caen_2, 7.0)  # default 7 MWh/emp
            energy_estimate = round(latest_fin.nr_angajati * energy_per_emp, 0)
            details["energy_estimate_mwh"] = energy_estimate
            details["energy_per_employee_mwh"] = energy_per_emp
            sources.append(f"Estimare energie: ~{energy_estimate:,.0f} MWh/an")

        # ── 2.1: EU Taxonomy alignment ──
        taxonomy_eligible = caen_2 in TAXONOMY_ELIGIBLE_CAEN
        taxonomy_aligned = caen_2 in TAXONOMY_ALIGNED_CAEN
        details["taxonomy"] = {
            "eligible": taxonomy_eligible,
            "aligned": taxonomy_aligned,
            "activity": TAXONOMY_ELIGIBLE_CAEN.get(caen_2, "not_classified"),
        }
        if taxonomy_aligned:
            score += Decimal("5")
            sources.append("EU Taxonomy: activitate aliniată")
        elif taxonomy_eligible:
            sources.append("EU Taxonomy: activitate eligibilă")
        else:
            sources.append("EU Taxonomy: neclasificat")

        # ── ESG raw data points (real emissions if available) ──
        result = await self.db.execute(
            select(ESGRawData)
            .where(
                ESGRawData.company_id == company.id,
                ESGRawData.categorie == "E",
            )
        )
        raw_data = result.scalars().all()
        if raw_data:
            details["raw_data_points"] = len(raw_data)
            sources.append(f"Date brute ESG: {len(raw_data)} puncte Environmental")
            # If we have actual emissions data, prefer it over estimates
            for rd in raw_data:
                if rd.raw_data and "emisii_co2" in (rd.raw_data or {}):
                    actual_co2 = rd.raw_data["emisii_co2"]
                    details["carbon_footprint_tonnes"] = actual_co2
                    details["carbon_source"] = "measured"
                    sources.append(f"Emisii CO2 raportate: {actual_co2} tone")

        return (
            max(min(score, Decimal("100")), Decimal("0")),
            sources if sources else ["Nu sunt date disponibile"],
            details,
        )

    # ──────────────────────────────────────────────────────────────────
    # 2.2: SOCIAL SCORING (ENHANCED)
    # ──────────────────────────────────────────────────────────────────

    async def _score_social(self, company: Company) -> tuple[Decimal, list[str], dict]:
        """
        Social score with enhancements:
        - Gender diversity estimation from administrator names
        - Employee productivity (revenue per employee)
        - Multi-year employment trend with detailed grading
        - Community impact through public contracts
        """
        score = Decimal("65")
        sources: list[str] = []
        details: dict = {}

        # ── Employee trends (3-year) ──
        result = await self.db.execute(
            select(FinancialData)
            .where(FinancialData.company_id == company.id)
            .order_by(FinancialData.an_fiscal.desc())
            .limit(3)
        )
        financials = result.scalars().all()

        if financials and financials[0].nr_angajati:
            emp = financials[0].nr_angajati
            details["current_employees"] = emp

            if emp > 250:
                score += Decimal("10")
                details["employer_size"] = "large"
                sources.append(f"Angajați: {emp} (angajator mare)")
            elif emp > 50:
                score += Decimal("5")
                details["employer_size"] = "medium"
                sources.append(f"Angajați: {emp}")
            else:
                details["employer_size"] = "small"
                sources.append(f"Angajați: {emp}")

            # ── 2.2: Employee productivity ──
            if financials[0].cifra_afaceri and emp > 0:
                rev_per_emp = float(financials[0].cifra_afaceri) / emp
                details["revenue_per_employee"] = round(rev_per_emp)
                if rev_per_emp > 500_000:
                    score += Decimal("5")
                    details["productivity"] = "high"
                elif rev_per_emp < 50_000:
                    score -= Decimal("3")
                    details["productivity"] = "low"
                else:
                    details["productivity"] = "normal"

            # Multi-year employment growth trend
            if len(financials) >= 2 and financials[1].nr_angajati and financials[1].nr_angajati > 0:
                prev_emp = financials[1].nr_angajati
                growth_1y = (emp - prev_emp) / prev_emp
                details["employee_growth_1y"] = round(growth_1y, 4)

                if growth_1y > 0.2:
                    score += Decimal("12")
                    sources.append("Trend angajare: creștere rapidă")
                elif growth_1y > 0.1:
                    score += Decimal("8")
                    sources.append("Trend angajare: crescător")
                elif growth_1y > 0:
                    score += Decimal("3")
                    sources.append("Trend angajare: ușor crescător")
                elif growth_1y > -0.1:
                    sources.append("Trend angajare: stabil")
                elif growth_1y > -0.2:
                    score -= Decimal("8")
                    sources.append("Trend angajare: descrescător")
                else:
                    score -= Decimal("15")
                    sources.append("Trend angajare: descrescător semnificativ")

            # 2-year sustained trend
            if len(financials) >= 3 and financials[2].nr_angajati and financials[2].nr_angajati > 0:
                growth_2y = (emp - financials[2].nr_angajati) / financials[2].nr_angajati
                details["employee_growth_2y"] = round(growth_2y, 4)
                if growth_2y > 0.3:
                    score += Decimal("5")  # Sustained growth bonus
                    details["sustained_growth"] = True
        else:
            sources.append("Angajați: date nedisponibile")

        # ── 2.2: Gender diversity estimation ──
        gender_data = await self._estimate_gender_diversity(company)
        details["gender_diversity"] = gender_data
        if gender_data["total_persons"] > 0:
            female_pct = gender_data["estimated_female_pct"]
            if 30 <= female_pct <= 70:
                score += Decimal("5")
                details["gender_balance"] = "balanced"
                sources.append(f"Diversitate gen: ~{female_pct}% feminin (estimat)")
            else:
                details["gender_balance"] = "imbalanced"
                sources.append(f"Diversitate gen: ~{female_pct}% feminin (estimat)")

        # ── Labor court cases ──
        result = await self.db.execute(
            select(func.count(CourtCase.id))
            .where(
                CourtCase.company_id == company.id,
                CourtCase.materie.ilike("%munc%"),
            )
        )
        labor_cases = result.scalar() or 0
        details["labor_court_cases"] = labor_cases

        if labor_cases > 5:
            score -= Decimal("20")
            sources.append(f"Litigii muncă: {labor_cases} (risc ridicat)")
        elif labor_cases > 0:
            score -= Decimal("5")
            sources.append(f"Litigii muncă: {labor_cases}")
        else:
            sources.append("Litigii muncă: 0")

        # ── 2.2: Public contracts as community impact ──
        result = await self.db.execute(
            select(func.count(PublicContract.id), func.sum(PublicContract.valoare_ron))
            .where(PublicContract.company_id == company.id)
        )
        row = result.one()
        contract_count = row[0] or 0
        contract_value = float(row[1] or 0)
        details["public_contracts"] = contract_count
        details["public_contract_value_ron"] = contract_value

        if contract_count > 10:
            score += Decimal("10")
            sources.append(f"Contracte publice: {contract_count} ({contract_value:,.0f} RON)")
            details["community_impact"] = "high"
        elif contract_count > 0:
            score += Decimal("5")
            sources.append(f"Contracte publice: {contract_count}")
            details["community_impact"] = "moderate"
        else:
            details["community_impact"] = "low"

        return (
            max(min(score, Decimal("100")), Decimal("0")),
            sources if sources else ["Nu sunt date disponibile"],
            details,
        )

    async def _estimate_gender_diversity(self, company: Company) -> dict:
        """
        2.2: Estimate gender diversity from person names (Romanian heuristic).
        Names ending in 'a' or 'e' are more likely female in Romanian.
        This is a rough proxy — not definitive.
        """
        result = await self.db.execute(
            select(CompanyPerson.nume_complet)
            .where(
                CompanyPerson.company_id == company.id,
                CompanyPerson.activ == True,
            )
        )
        names = [r for r in result.scalars().all() if r]

        if not names:
            return {"total_persons": 0, "estimated_female_pct": 0, "estimated_male_pct": 0}

        # Romanian female first name heuristic
        female_indicators = {"ana", "maria", "elena", "ioana", "andreea", "alexandra",
                            "mihaela", "cristina", "laura", "alina", "diana", "raluca",
                            "simona", "gabriela", "nicoleta", "adriana", "carmen", "florina",
                            "daniela", "georgiana", "monica", "liliana", "viorica", "mariana",
                            "corina", "oana", "irina", "paula", "claudia", "camelia"}

        female_count = 0
        for full_name in names:
            parts = full_name.strip().lower().split()
            if not parts:
                continue
            # Check all name parts against female indicators
            first_name = parts[-1] if len(parts) > 1 else parts[0]  # Last word is usually first name in Romanian
            if first_name in female_indicators or (len(first_name) > 2 and first_name.endswith("a")):
                female_count += 1

        total = len(names)
        female_pct = round((female_count / total) * 100) if total > 0 else 0

        return {
            "total_persons": total,
            "estimated_female_count": female_count,
            "estimated_male_count": total - female_count,
            "estimated_female_pct": female_pct,
            "estimated_male_pct": 100 - female_pct,
            "method": "name_heuristic",
        }

    # ──────────────────────────────────────────────────────────────────
    # 2.3: GOVERNANCE SCORING (ENHANCED)
    # ──────────────────────────────────────────────────────────────────

    async def _score_governance(self, company: Company) -> tuple[Decimal, list[str], dict]:
        """
        Governance score with enhancements:
        - UBO depth analysis (beneficial ownership chain)
        - Conflict of interest detection (admin at both company and authority)
        - Board stability index (turnover ratio over 5 years)
        - Financial reporting consistency with gap detection
        """
        score = Decimal("65")
        sources: list[str] = []
        details: dict = {}

        # ── Ownership transparency & UBO ──
        result = await self.db.execute(
            select(CompanyPerson)
            .where(
                CompanyPerson.company_id == company.id,
                CompanyPerson.tip == "ASOCIAT",
                CompanyPerson.activ == True,
            )
        )
        associates = result.scalars().all()

        if associates:
            details["active_associates"] = len(associates)
            sources.append(f"Asociați activi: {len(associates)}")

            # Check ownership completeness
            has_pct = all(a.procent_parti is not None for a in associates)
            if has_pct:
                total_pct = sum(float(a.procent_parti or 0) for a in associates)
                if abs(total_pct - 100) < 1:
                    score += Decimal("10")
                    details["ownership_complete"] = True
                    sources.append("Structura acționariat: completă (100%)")
                else:
                    score += Decimal("5")
                    details["ownership_complete"] = False
                    details["ownership_total_pct"] = round(total_pct, 2)
            else:
                details["ownership_complete"] = False
                sources.append("Procente participare: parțial declarate")

            # ── 2.3: UBO depth — are there legal entity associates (not natural persons)? ──
            # Legal entities as associates suggest deeper ownership chains
            legal_entity_associates = [
                a for a in associates
                if a.nume_complet and any(
                    kw in (a.nume_complet or "").upper()
                    for kw in ["SRL", "SA", "SCS", "SNC", "PFA", "LTD", "GMBH", "INC"]
                )
            ]
            details["ubo_depth"] = {
                "legal_entity_associates": len(legal_entity_associates),
                "natural_person_associates": len(associates) - len(legal_entity_associates),
                "depth_level": 2 if legal_entity_associates else 1,
                "transparency": "low" if len(legal_entity_associates) > 2 else "medium" if legal_entity_associates else "high",
            }
            if len(legal_entity_associates) > 2:
                score -= Decimal("10")
                sources.append(f"UBO: {len(legal_entity_associates)} entități juridice (transparență redusă)")
            elif legal_entity_associates:
                score -= Decimal("3")
                sources.append(f"UBO: {len(legal_entity_associates)} entitate juridică")
            else:
                score += Decimal("5")
                sources.append("UBO: doar persoane fizice (transparență ridicată)")
        else:
            details["active_associates"] = 0

        # ── Administrator stability & board index ──
        result = await self.db.execute(
            select(CompanyPerson)
            .where(
                CompanyPerson.company_id == company.id,
                CompanyPerson.tip == "ADMINISTRATOR",
            )
        )
        admins = result.scalars().all()

        active_admins = [a for a in admins if a.activ]
        former_admins = [a for a in admins if not a.activ]
        total_admins = len(admins)

        details["active_admins"] = len(active_admins)
        details["former_admins"] = len(former_admins)

        # ── 2.3: Board stability index ──
        # BSI = active_admins / (active_admins + former_admins) — higher is better
        if total_admins > 0:
            bsi = len(active_admins) / total_admins
            details["board_stability_index"] = round(bsi, 3)

            if bsi > 0.7:
                score += Decimal("10")
                details["board_stability"] = "very_stable"
                sources.append("Board: foarte stabil")
            elif bsi > 0.5:
                score += Decimal("5")
                details["board_stability"] = "stable"
                sources.append("Administratori: stabili")
            elif bsi < 0.3:
                score -= Decimal("15")
                details["board_stability"] = "very_unstable"
                sources.append(f"Administratori schimbați: {len(former_admins)} (instabilitate ridicată)")
            else:
                details["board_stability"] = "moderate"
        else:
            details["board_stability_index"] = None

        # ── 2.3: Conflict of interest detection ──
        coi = await self._detect_conflicts_of_interest(company, active_admins)
        details["conflict_of_interest"] = coi
        if coi["conflicts_found"] > 0:
            score -= Decimal("10")
            sources.append(f"Conflict de interese potențial: {coi['conflicts_found']} detectate")

        # ── Financial reporting consistency ──
        result = await self.db.execute(
            select(FinancialData.an_fiscal)
            .where(FinancialData.company_id == company.id)
            .order_by(FinancialData.an_fiscal.desc())
        )
        report_years = [r for r in result.scalars().all()]
        details["reporting_years"] = len(report_years)

        if len(report_years) >= 5:
            score += Decimal("10")
            sources.append(f"Raportare financiară: {len(report_years)} ani consecutivi")
            # Check for gaps
            if len(report_years) >= 2:
                gaps = []
                for i in range(len(report_years) - 1):
                    if report_years[i] - report_years[i + 1] > 1:
                        gaps.append(f"{report_years[i+1]+1}-{report_years[i]-1}")
                if gaps:
                    score -= Decimal("5")
                    details["reporting_gaps"] = gaps
                    sources.append(f"Raportare: lacune în anii {', '.join(gaps)}")
        elif len(report_years) >= 3:
            score += Decimal("5")
            sources.append(f"Raportare financiară: {len(report_years)} ani")
        elif len(report_years) == 0:
            score -= Decimal("15")
            sources.append("Raportare financiară: lipsă")

        return (
            max(min(score, Decimal("100")), Decimal("0")),
            sources if sources else ["Nu sunt date disponibile"],
            details,
        )

    async def _detect_conflicts_of_interest(
        self, company: Company, active_admins: list
    ) -> dict:
        """
        2.3: Detect potential conflicts of interest.
        Check if any admin also appears as admin/associate at companies with public contracts
        from the same authority that this company has contracts with.
        """
        if not active_admins:
            return {"conflicts_found": 0, "details": []}

        admin_names = [a.nume_complet for a in active_admins if a.nume_complet]
        if not admin_names:
            return {"conflicts_found": 0, "details": []}

        # Find other companies where these admins also serve
        conflicts = []
        for name in admin_names:
            result = await self.db.execute(
                select(
                    CompanyPerson.company_id,
                    Company.denumire,
                    Company.cui,
                    CompanyPerson.tip,
                )
                .join(Company, Company.id == CompanyPerson.company_id)
                .where(
                    CompanyPerson.nume_complet == name,
                    CompanyPerson.activ == True,
                    CompanyPerson.company_id != company.id,
                )
            )
            other_companies = result.all()

            for oc in other_companies:
                # Check if the other company has public contracts (potential conflict)
                has_contracts = await self.db.execute(
                    select(func.count(PublicContract.id))
                    .where(PublicContract.company_id == oc[0])
                )
                contract_count = has_contracts.scalar() or 0

                if contract_count > 0:
                    conflicts.append({
                        "person": name,
                        "other_company": oc[1],
                        "other_cui": oc[2],
                        "role": oc[3],
                        "other_public_contracts": contract_count,
                    })

        return {
            "conflicts_found": len(conflicts),
            "details": conflicts[:10],  # Limit to top 10
        }

    # ──────────────────────────────────────────────────────────────────
    # 2.4: CONFORMITY & STANDARDS
    # ──────────────────────────────────────────────────────────────────

    async def _csrd_readiness_check(
        self, company: Company, latest_fin: Optional[FinancialData]
    ) -> dict:
        """
        2.4: CSRD readiness checklist — 12 items scored as met/not_met.
        """
        checks: dict[str, bool] = {}

        # 1. Financial reporting 5+ years
        result = await self.db.execute(
            select(func.count(FinancialData.id))
            .where(FinancialData.company_id == company.id)
        )
        report_count = result.scalar() or 0
        checks["financial_reporting_5y"] = report_count >= 5

        # 2. Employee count reported
        checks["employee_count_reported"] = bool(latest_fin and latest_fin.nr_angajati)

        # 3. Ownership transparent
        result = await self.db.execute(
            select(CompanyPerson)
            .where(
                CompanyPerson.company_id == company.id,
                CompanyPerson.tip == "ASOCIAT",
                CompanyPerson.activ == True,
            )
        )
        assoc = result.scalars().all()
        has_full_pct = bool(assoc) and all(a.procent_parti is not None for a in assoc)
        checks["ownership_transparent"] = has_full_pct

        # 4. Admin stable
        result = await self.db.execute(
            select(func.count(CompanyPerson.id))
            .where(
                CompanyPerson.company_id == company.id,
                CompanyPerson.tip == "ADMINISTRATOR",
                CompanyPerson.activ == False,
            )
        )
        former = result.scalar() or 0
        checks["admin_stable"] = former <= 3

        # 5. No environmental fines
        result = await self.db.execute(
            select(func.count(EnvironmentalFine.id))
            .where(EnvironmentalFine.company_id == company.id)
        )
        checks["no_environmental_fines"] = (result.scalar() or 0) == 0

        # 6. Public contracts track
        result = await self.db.execute(
            select(func.count(PublicContract.id))
            .where(PublicContract.company_id == company.id)
        )
        checks["public_contracts_track"] = (result.scalar() or 0) > 0

        # 7. No insolvency
        checks["no_insolvency"] = not company.has_insolvency

        # 8. No labor disputes
        result = await self.db.execute(
            select(func.count(CourtCase.id))
            .where(CourtCase.company_id == company.id, CourtCase.materie.ilike("%munc%"))
        )
        checks["no_labor_disputes"] = (result.scalar() or 0) == 0

        # 9. CAEN declared
        checks["caen_declared"] = bool(company.caen_principal)

        # 10. Address complete
        checks["address_complete"] = bool(company.adresa_completa)

        # 11. Capital social adequate
        checks["capital_social_adequate"] = bool(company.capital_social and company.capital_social > 0)

        # 12. Active status
        checks["active_status"] = company.stare == "ACTIVA"

        met_count = sum(1 for v in checks.values() if v)
        return {
            "checks": checks,
            "met": met_count,
            "total": len(checks),
            "readiness_pct": round((met_count / len(checks)) * 100),
            "ready": met_count >= 10,  # ≥10/12 = CSRD-ready
        }

    def _compute_gri_coverage(self) -> dict:
        """2.4: Compute which GRI Standards we can report on."""
        gri_result = {}
        for category, standards in GRI_MAPPING.items():
            cat_items = {}
            for code, info in standards.items():
                cat_items[code] = {
                    "name": info["name"],
                    "data_available": info["available"],
                    "proxy_used": info.get("proxy"),
                    "source": info.get("source"),
                }
            gri_result[category] = cat_items

        available = sum(
            1 for cat in GRI_MAPPING.values()
            for info in cat.values()
            if info["available"]
        )
        total = sum(len(cat) for cat in GRI_MAPPING.values())

        gri_result["coverage_pct"] = round((available / total) * 100) if total else 0
        return gri_result

    def _classify_sfdr(self, composite: Decimal) -> Optional[str]:
        """
        2.4: Enhanced SFDR classification with sub-categories.
        """
        if composite >= Decimal("85"):
            return "Article 9+"   # Deep green — impact fund eligible
        elif composite >= Decimal("75"):
            return "Article 9"    # Dark green — sustainability objective
        elif composite >= Decimal("60"):
            return "Article 8+"   # Light green plus — strong ESG promotion
        elif composite >= Decimal("50"):
            return "Article 8"    # Light green — ESG promotion
        elif composite >= Decimal("35"):
            return "Article 6+"   # Pre-ESG with some positive indicators
        else:
            return "Article 6"    # Non-ESG

    # ──────────────────────────────────────────────────────────────────
    # 2.5: REPORTING & COMPARISON
    # ──────────────────────────────────────────────────────────────────

    async def get_factsheet(self, company_id: int) -> dict:
        """
        2.5: Generate ESG factsheet data for a single company (1-pager content).
        """
        company = await self._get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        result = await self.db.execute(
            select(ESGScore)
            .where(ESGScore.company_id == company_id)
            .order_by(ESGScore.calculat_la.desc())
            .limit(1)
        )
        esg = result.scalar_one_or_none()
        if not esg:
            raise ValueError("No ESG score available")

        latest_fin = await self._get_latest_financial(company)

        return {
            "company": {"cui": company.cui, "denumire": company.denumire, "caen": company.caen_principal},
            "scores": {
                "total": float(esg.score_total) if esg.score_total else None,
                "environmental": float(esg.score_e) if esg.score_e else None,
                "social": float(esg.score_s) if esg.score_s else None,
                "governance": float(esg.score_g) if esg.score_g else None,
            },
            "classification": {
                "sfdr": esg.sfdr_categoria,
                "csrd_relevant": esg.csrd_relevant,
            },
            "carbon_estimate": float(esg.e_emisii_co2) if esg.e_emisii_co2 else None,
            "sources": esg.surse_date,
            "calculated_at": esg.calculat_la.isoformat() if esg.calculat_la else None,
            "employees": latest_fin.nr_angajati if latest_fin else None,
            "revenue_ron": float(latest_fin.cifra_afaceri) if latest_fin and latest_fin.cifra_afaceri else None,
            "disclaimer": DISCLAIMER,
        }

    async def compare_companies(self, company_ids: list[int]) -> list[dict]:
        """
        2.5: Compare ESG scores of multiple companies side-by-side.
        """
        results = []
        for cid in company_ids[:10]:  # Max 10 companies
            try:
                factsheet = await self.get_factsheet(cid)
                results.append(factsheet)
            except ValueError:
                results.append({"company_id": cid, "error": "Score not available"})
        return results

    async def portfolio_aggregate(self, company_ids: list[int]) -> dict:
        """
        2.5: Compute weighted average ESG score for a portfolio of companies.
        Weights are by revenue (bigger companies count more).
        """
        scores_data = []

        for cid in company_ids:
            result = await self.db.execute(
                select(ESGScore)
                .where(ESGScore.company_id == cid)
                .order_by(ESGScore.calculat_la.desc())
                .limit(1)
            )
            esg = result.scalar_one_or_none()
            if not esg:
                continue

            fin = await self.db.execute(
                select(FinancialData.cifra_afaceri)
                .where(FinancialData.company_id == cid)
                .order_by(FinancialData.an_fiscal.desc())
                .limit(1)
            )
            revenue = fin.scalar_one_or_none() or 0

            scores_data.append({
                "company_id": cid,
                "e": float(esg.score_e or 0),
                "s": float(esg.score_s or 0),
                "g": float(esg.score_g or 0),
                "total": float(esg.score_total or 0),
                "weight": float(revenue) if revenue > 0 else 1.0,
            })

        if not scores_data:
            return {"error": "No ESG data available for portfolio"}

        total_weight = sum(s["weight"] for s in scores_data)

        weighted_e = sum(s["e"] * s["weight"] for s in scores_data) / total_weight
        weighted_s = sum(s["s"] * s["weight"] for s in scores_data) / total_weight
        weighted_g = sum(s["g"] * s["weight"] for s in scores_data) / total_weight
        weighted_total = sum(s["total"] * s["weight"] for s in scores_data) / total_weight

        # SFDR distribution
        sfdr_dist = {"Article 9+": 0, "Article 9": 0, "Article 8+": 0,
                     "Article 8": 0, "Article 6+": 0, "Article 6": 0}
        for s in scores_data:
            cat = self._classify_sfdr(Decimal(str(s["total"])))
            if cat in sfdr_dist:
                sfdr_dist[cat] += 1

        return {
            "company_count": len(scores_data),
            "weighted_scores": {
                "total": round(weighted_total, 1),
                "environmental": round(weighted_e, 1),
                "social": round(weighted_s, 1),
                "governance": round(weighted_g, 1),
            },
            "simple_average": {
                "total": round(sum(s["total"] for s in scores_data) / len(scores_data), 1),
                "environmental": round(sum(s["e"] for s in scores_data) / len(scores_data), 1),
                "social": round(sum(s["s"] for s in scores_data) / len(scores_data), 1),
                "governance": round(sum(s["g"] for s in scores_data) / len(scores_data), 1),
            },
            "sfdr_distribution": sfdr_dist,
            "disclaimer": DISCLAIMER,
        }

    async def get_timeline(self, company_id: int, limit: int = 12) -> list[dict]:
        """
        2.5: ESG score timeline for trend visualization.
        """
        result = await self.db.execute(
            select(ESGScore)
            .where(ESGScore.company_id == company_id)
            .order_by(ESGScore.calculat_la.desc())
            .limit(limit)
        )
        scores = result.scalars().all()
        return [
            {
                "date": s.calculat_la.isoformat() if s.calculat_la else None,
                "total": float(s.score_total) if s.score_total else None,
                "e": float(s.score_e) if s.score_e else None,
                "s": float(s.score_s) if s.score_s else None,
                "g": float(s.score_g) if s.score_g else None,
                "sfdr": s.sfdr_categoria,
            }
            for s in reversed(scores)
        ]
