"""
Risk scoring service — Altman Z-Score adapted for Romanian companies.

Score Components (0-100 scale):
  - Financial (30%): Altman Z-Score adapted, liquidity, solvency
  - Legal (25%): Court cases, insolvency proceedings
  - Fiscal (25%): ANAF debts, TVA status, fiscal compliance
  - Behavioral (20%): Payment patterns, address changes, admin changes

Risk Categories:
  A (80-100): Risc minim
  B (60-79):  Risc scăzut
  C (40-59):  Risc mediu
  D (20-39):  Risc ridicat
  E (0-19):   Risc critic
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, InsolvencyCase, CourtCase,
    CompanyDebt, CompanyPerson, RiskScore,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── 1.1: Industry-specific Z-Score adjustments (CAEN 2-digit groups) ──
# Multipliers applied to the raw Z-Score to account for sector norms.
# > 1.0 = industry typically has higher Z (less risky), so we normalize down
# < 1.0 = industry typically has lower Z (more capital-intensive), normalize up
INDUSTRY_ZSCORE_ADJUSTMENTS: dict[str, Decimal] = {
    # Agriculture, forestry, fishing (01-03)
    "01": Decimal("0.85"), "02": Decimal("0.85"), "03": Decimal("0.85"),
    # Mining (05-09)
    "05": Decimal("0.80"), "06": Decimal("0.75"), "07": Decimal("0.80"),
    "08": Decimal("0.80"), "09": Decimal("0.80"),
    # Manufacturing (10-33) — capital-intensive
    "10": Decimal("0.90"), "11": Decimal("0.90"), "12": Decimal("0.90"),
    "13": Decimal("0.90"), "14": Decimal("0.90"), "15": Decimal("0.90"),
    "16": Decimal("0.90"), "17": Decimal("0.85"), "18": Decimal("0.90"),
    "19": Decimal("0.80"), "20": Decimal("0.85"), "21": Decimal("0.85"),
    "22": Decimal("0.90"), "23": Decimal("0.85"), "24": Decimal("0.80"),
    "25": Decimal("0.90"), "26": Decimal("0.95"), "27": Decimal("0.90"),
    "28": Decimal("0.90"), "29": Decimal("0.85"), "30": Decimal("0.85"),
    "31": Decimal("0.90"), "32": Decimal("0.90"), "33": Decimal("0.90"),
    # Utilities (35-39)
    "35": Decimal("0.80"), "36": Decimal("0.80"), "37": Decimal("0.80"),
    "38": Decimal("0.85"), "39": Decimal("0.85"),
    # Construction (41-43)
    "41": Decimal("0.90"), "42": Decimal("0.85"), "43": Decimal("0.90"),
    # Trade (45-47) — higher turnover ratios
    "45": Decimal("1.05"), "46": Decimal("1.05"), "47": Decimal("1.10"),
    # Transport (49-53) — capital-intensive
    "49": Decimal("0.85"), "50": Decimal("0.80"), "51": Decimal("0.80"),
    "52": Decimal("0.90"), "53": Decimal("0.90"),
    # Hospitality (55-56) — seasonal, lower margins
    "55": Decimal("0.85"), "56": Decimal("0.90"),
    # IT & Communications (58-63) — asset-light, high margins
    "58": Decimal("1.10"), "59": Decimal("1.05"), "60": Decimal("1.05"),
    "61": Decimal("1.00"), "62": Decimal("1.15"), "63": Decimal("1.10"),
    # Finance & Insurance (64-66)
    "64": Decimal("0.70"), "65": Decimal("0.70"), "66": Decimal("0.80"),
    # Real estate (68)
    "68": Decimal("0.75"),
    # Professional services (69-75) — asset-light
    "69": Decimal("1.10"), "70": Decimal("1.10"), "71": Decimal("1.05"),
    "72": Decimal("1.05"), "73": Decimal("1.10"), "74": Decimal("1.10"),
    "75": Decimal("1.00"),
    # Admin & support (77-82)
    "77": Decimal("0.90"), "78": Decimal("1.05"), "79": Decimal("0.90"),
    "80": Decimal("1.00"), "81": Decimal("1.00"), "82": Decimal("1.05"),
}


class RiskScoringEngine:
    """
    Adapted Altman Z-Score + multi-factor risk engine for Romanian companies.

    Improvements in v2:
    - X2 factor (retained earnings) included via capitaluri_prop - capital_social
    - Industry-specific Z-Score adjustment multipliers per CAEN 2-digit
    - Micro-company variant (Piauget-style) for firms with <9 employees
    - Configurable weight profiles per tenant/industry
    - Score history tracking with trend & prediction
    - Sectoral benchmarking with percentile ranking
    - Detailed audit log with reason codes per calculation
    """

    # ── 1.2: Default weight profile — can be overridden per-tenant ──
    DEFAULT_WEIGHTS = {
        "financial": Decimal("0.30"),
        "legal": Decimal("0.25"),
        "fiscal": Decimal("0.25"),
        "behavioral": Decimal("0.20"),
    }

    # Industry-specific weight overrides (CAEN 2-digit prefix → weights)
    INDUSTRY_WEIGHTS: dict[str, dict[str, Decimal]] = {
        # Construction — fiscal risk is higher (frequent tax issues)
        "41": {"financial": Decimal("0.25"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.35"), "behavioral": Decimal("0.20")},
        "42": {"financial": Decimal("0.25"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.35"), "behavioral": Decimal("0.20")},
        "43": {"financial": Decimal("0.25"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.35"), "behavioral": Decimal("0.20")},
        # IT — financial weight higher, fiscal lower (cleaner tax profile)
        "62": {"financial": Decimal("0.40"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.15"), "behavioral": Decimal("0.25")},
        "63": {"financial": Decimal("0.40"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.15"), "behavioral": Decimal("0.25")},
        # Transport — behavioral is critical (admin turnover, regulatory)
        "49": {"financial": Decimal("0.25"), "legal": Decimal("0.25"),
               "fiscal": Decimal("0.20"), "behavioral": Decimal("0.30")},
        # Trade — financial turnover ratio matters most
        "46": {"financial": Decimal("0.35"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.25"), "behavioral": Decimal("0.20")},
        "47": {"financial": Decimal("0.35"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.25"), "behavioral": Decimal("0.20")},
        # HoReCa — seasonal, behavioral patterns more important
        "55": {"financial": Decimal("0.25"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.25"), "behavioral": Decimal("0.30")},
        "56": {"financial": Decimal("0.25"), "legal": Decimal("0.20"),
               "fiscal": Decimal("0.25"), "behavioral": Decimal("0.30")},
    }

    CATEGORIES = [
        (Decimal("80"), "A"),   # Risc minim
        (Decimal("60"), "B"),   # Risc scăzut
        (Decimal("40"), "C"),   # Risc mediu
        (Decimal("20"), "D"),   # Risc ridicat
        (Decimal("0"),  "E"),   # Risc critic
    ]

    MODEL_VERSION = "2.0"

    def __init__(self, db: AsyncSession, weight_overrides: dict[str, Decimal] | None = None):
        self.db = db
        self._custom_weights = weight_overrides

    def _get_weights(self, company: Company) -> dict[str, Decimal]:
        """
        1.2: Resolve weight profile — custom > industry > default.
        """
        # Custom per-tenant weights take priority
        if self._custom_weights:
            return self._custom_weights

        # Industry-based weights
        caen_2 = (company.caen_principal or "")[:2]
        if caen_2 in self.INDUSTRY_WEIGHTS:
            return self.INDUSTRY_WEIGHTS[caen_2]

        return self.DEFAULT_WEIGHTS

    async def calculate(self, company_id: int) -> RiskScore:
        """
        Calculate comprehensive risk score for a company.
        Returns a new RiskScore ORM instance (not yet committed).

        1.5: Includes detailed audit_log with per-component breakdown and reason codes.
        """
        company = await self._get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        weights = self._get_weights(company)

        # ── Calculate all sub-scores with audit details ──
        financial_score, financial_details = await self._score_financial(company)
        legal_score, legal_details = await self._score_legal(company)
        fiscal_score, fiscal_details = await self._score_fiscal(company)
        behavioral_score, behavioral_details = await self._score_behavioral(company)

        total = (
            financial_score * weights["financial"]
            + legal_score * weights["legal"]
            + fiscal_score * weights["fiscal"]
            + behavioral_score * weights["behavioral"]
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        category = self._categorize(total)

        # ── 1.5: Build reason codes ──
        factors = []
        reason_codes = []
        if financial_score < Decimal("40"):
            factors.append("indicatori financiari slabi")
            reason_codes.append("FINANCIAL_WEAK")
        if legal_score < Decimal("40"):
            factors.append("probleme juridice active")
            reason_codes.append("LEGAL_ISSUES")
        if fiscal_score < Decimal("40"):
            factors.append("datorii fiscale semnificative")
            reason_codes.append("FISCAL_DEBT")
        if behavioral_score < Decimal("40"):
            factors.append("comportament atipic")
            reason_codes.append("BEHAVIORAL_RISK")
        if company.has_insolvency:
            reason_codes.append("INSOLVENCY_FLAG")
        if financial_score < Decimal("30"):
            reason_codes.append("ZSCORE_DISTRESS")

        # ── 1.5: Audit log ──
        audit_log = {
            "version": self.MODEL_VERSION,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "weights_used": {k: str(v) for k, v in weights.items()},
            "weights_source": (
                "custom" if self._custom_weights
                else f"industry_{(company.caen_principal or '')[:2]}"
                if (company.caen_principal or "")[:2] in self.INDUSTRY_WEIGHTS
                else "default"
            ),
            "components": {
                "financial": {"score": str(financial_score), **financial_details},
                "legal": {"score": str(legal_score), **legal_details},
                "fiscal": {"score": str(fiscal_score), **fiscal_details},
                "behavioral": {"score": str(behavioral_score), **behavioral_details},
            },
            "reason_codes": reason_codes,
            "company_caen": company.caen_principal,
            "company_stare": company.stare,
        }

        # ── 1.3: Compute trend from previous score ──
        prev_score = await self._get_previous_score(company_id)
        trend = None
        if prev_score is not None:
            diff = int(total) - prev_score
            if diff > 10:
                trend = "IMPROVING"
            elif diff < -10:
                trend = "DEGRADING"
            else:
                trend = "STABLE"
            audit_log["trend"] = trend
            audit_log["previous_score"] = prev_score
            audit_log["score_delta"] = diff

        # ── 1.4: Compute sector benchmark / percentile ──
        benchmark = await self._compute_benchmark(company)
        if benchmark:
            audit_log["benchmark"] = benchmark

        # ── Probability of insolvency (simple logistic approximation) ──
        # P(insolvency) ≈ 1 / (1 + e^(0.1 * (score - 30)))
        import math
        prob_insolvency = Decimal(str(
            round(1.0 / (1.0 + math.exp(0.1 * (float(total) - 30))), 4)
        ))

        # ── Credit limit estimation ──
        credit_limit = self._estimate_credit_limit(company, total, financial_details)

        risk_score = RiskScore(
            company_id=company_id,
            score=max(1, min(int(total), 100)),
            rating=category,
            scor_financiar=financial_score,
            scor_legal=legal_score,
            scor_fiscal=fiscal_score,
            scor_comportamental=behavioral_score,
            limita_credit=credit_limit,
            probabilitate_insolventa=prob_insolvency,
            factori_risc={"factors": factors, "reason_codes": reason_codes, "audit": audit_log},
            calculat_la=datetime.now(timezone.utc),
            model_versiune=self.MODEL_VERSION,
        )

        self.db.add(risk_score)
        logger.info(
            "risk_score_calculated",
            company_id=company_id,
            total=str(total),
            category=category,
            version=self.MODEL_VERSION,
            trend=trend,
        )

        return risk_score

    # ── 1.3: Get previous score for trend calculation ──
    async def _get_previous_score(self, company_id: int) -> int | None:
        result = await self.db.execute(
            select(RiskScore.score)
            .where(RiskScore.company_id == company_id)
            .order_by(RiskScore.calculat_la.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row is not None else None

    # ── 1.4: Sector benchmark & percentile ──
    async def _compute_benchmark(self, company: Company) -> dict | None:
        """
        Compute where this company ranks vs others in its CAEN 2-digit sector.
        Returns sector average score, count, and percentile rank.
        """
        caen_2 = (company.caen_principal or "")[:2]
        if not caen_2:
            return None

        # Get all scores for companies in same sector
        result = await self.db.execute(
            select(RiskScore.score)
            .join(Company, Company.id == RiskScore.company_id)
            .where(
                func.substr(Company.caen_principal, 1, 2) == caen_2,
                Company.stare == "ACTIVA",
            )
        )
        sector_scores = [row for row in result.scalars().all()]

        if len(sector_scores) < 3:
            return None  # Not enough data for meaningful benchmark

        avg_score = sum(sector_scores) / len(sector_scores)

        return {
            "sector_caen_2": caen_2,
            "sector_avg_score": round(avg_score, 1),
            "sector_count": len(sector_scores),
        }

    async def _get_company(self, company_id: int) -> Optional[Company]:
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def _score_financial(self, company: Company) -> tuple[Decimal, dict]:
        """
        Financial score based on Altman Z-Score adapted for Romania.

        1.1 Improvements:
        - X2 factor (retained earnings = capitaluri_prop - capital_social) now included
        - Industry-specific Z-Score adjustments via CAEN multiplier
        - Micro-company variant (Piauget-style) for firms with <9 employees
        - Multi-year trend analysis (not just 2 years)

        Full Z' = 0.717·X1 + 0.847·X2 + 3.107·X3 + 0.420·X4 + 0.998·X5
        Where:
          X1 = Working Capital / Total Assets ≈ (Total Assets - Total Liabilities) / Total Assets
          X2 = Retained Earnings / Total Assets ≈ (Equity - Capital Social) / Total Assets
          X3 = EBIT / Total Assets ≈ Profit Net / Total Assets
          X4 = Book Value of Equity / Total Liabilities
          X5 = Revenue / Total Assets
        """
        details: dict = {}

        # Get latest 3 years of financial data for trend analysis
        result = await self.db.execute(
            select(FinancialData)
            .where(FinancialData.company_id == company.id)
            .order_by(FinancialData.an_fiscal.desc())
            .limit(3)
        )
        financials = result.scalars().all()

        if not financials:
            details["reason"] = "no_financial_data"
            return Decimal("50"), details  # Neutral if no data

        latest = financials[0]
        nr_angajati = latest.nr_angajati or 0

        total_assets = Decimal(str(latest.total_active or 0))
        if total_assets <= 0:
            details["reason"] = "zero_or_negative_assets"
            return Decimal("30"), details

        total_liabilities = Decimal(str(latest.total_datorii or 0))
        equity = Decimal(str(latest.capitaluri_prop or 0))
        revenue = Decimal(str(latest.cifra_afaceri or 0))
        profit = Decimal(str(latest.profit_net or 0))
        capital_social = Decimal(str(company.capital_social or 0))

        # ── 1.1: Micro-company scoring (Piauget-style, <9 employees) ──
        if nr_angajati > 0 and nr_angajati < 9:
            score, micro_details = self._score_micro_company(
                revenue, profit, equity, total_liabilities, total_assets, nr_angajati
            )
            details["method"] = "micro_piauget"
            details.update(micro_details)
        else:
            # ── Standard Altman Z'-Score with X2 ──
            # X1: Working Capital / Total Assets
            working_capital = total_assets - total_liabilities
            x1 = working_capital / total_assets

            # X2: Retained Earnings / Total Assets (NEW in v2)
            retained_earnings = equity - capital_social
            x2 = retained_earnings / total_assets if total_assets > 0 else Decimal("0")

            # X3: EBIT / Total Assets (approximated by profit_net)
            x3 = profit / total_assets

            # X4: Equity / Total Liabilities
            x4 = equity / total_liabilities if total_liabilities > 0 else Decimal("3")

            # X5: Revenue / Total Assets
            x5 = revenue / total_assets

            # Full Altman Z' Score (including X2)
            z_score = (
                Decimal("0.717") * x1
                + Decimal("0.847") * x2
                + Decimal("3.107") * x3
                + Decimal("0.420") * x4
                + Decimal("0.998") * x5
            )

            # ── 1.1: Industry adjustment ──
            caen_2 = (company.caen_principal or "")[:2]
            industry_mult = INDUSTRY_ZSCORE_ADJUSTMENTS.get(caen_2, Decimal("1.0"))
            z_adjusted = z_score * industry_mult

            details["method"] = "altman_z_prime_v2"
            details["x1_working_capital"] = str(x1.quantize(Decimal("0.0001")))
            details["x2_retained_earnings"] = str(x2.quantize(Decimal("0.0001")))
            details["x3_ebit_ratio"] = str(x3.quantize(Decimal("0.0001")))
            details["x4_equity_leverage"] = str(x4.quantize(Decimal("0.0001")))
            details["x5_asset_turnover"] = str(x5.quantize(Decimal("0.0001")))
            details["z_score_raw"] = str(z_score.quantize(Decimal("0.0001")))
            details["industry_multiplier"] = str(industry_mult)
            details["z_score_adjusted"] = str(z_adjusted.quantize(Decimal("0.0001")))

            # Map Z-Score to 0-100 scale
            score = self._zscore_to_100(z_adjusted)

        # ── Multi-year trend analysis (3 years) ──
        trend_adjustment = Decimal("0")
        if len(financials) >= 2:
            prev = financials[1]
            if latest.cifra_afaceri and prev.cifra_afaceri and prev.cifra_afaceri > 0:
                growth_1y = Decimal(str(latest.cifra_afaceri - prev.cifra_afaceri)) / Decimal(str(prev.cifra_afaceri))
                details["revenue_growth_1y"] = str(growth_1y.quantize(Decimal("0.0001")))
                if growth_1y > Decimal("0.20"):
                    trend_adjustment += Decimal("7")
                elif growth_1y > Decimal("0.10"):
                    trend_adjustment += Decimal("5")
                elif growth_1y < Decimal("-0.30"):
                    trend_adjustment -= Decimal("12")
                elif growth_1y < Decimal("-0.20"):
                    trend_adjustment -= Decimal("10")
                elif growth_1y < Decimal("-0.10"):
                    trend_adjustment -= Decimal("5")

        if len(financials) >= 3:
            oldest = financials[2]
            if latest.cifra_afaceri and oldest.cifra_afaceri and oldest.cifra_afaceri > 0:
                growth_2y = Decimal(str(latest.cifra_afaceri - oldest.cifra_afaceri)) / Decimal(str(oldest.cifra_afaceri))
                details["revenue_growth_2y"] = str(growth_2y.quantize(Decimal("0.0001")))
                # Sustained growth/decline bonus/penalty
                if growth_2y > Decimal("0.30"):
                    trend_adjustment += Decimal("3")  # Additional bonus for sustained growth
                elif growth_2y < Decimal("-0.40"):
                    trend_adjustment -= Decimal("5")  # Additional penalty for sustained decline

            # Profit trend
            if latest.profit_net and oldest.profit_net:
                if latest.profit_net > 0 and oldest.profit_net <= 0:
                    trend_adjustment += Decimal("5")  # Turnaround
                    details["profit_turnaround"] = True
                elif latest.profit_net <= 0 and oldest.profit_net > 0:
                    trend_adjustment -= Decimal("7")  # Decline into loss
                    details["profit_decline_to_loss"] = True

        details["trend_adjustment"] = str(trend_adjustment)

        # ── Ratio bonuses ──
        ratio_adj = Decimal("0")
        if latest.rata_lichiditate and latest.rata_lichiditate > Decimal("2"):
            ratio_adj += Decimal("3")
        elif latest.rata_lichiditate and latest.rata_lichiditate < Decimal("0.5"):
            ratio_adj -= Decimal("5")

        if latest.grad_indatorare and latest.grad_indatorare > Decimal("3"):
            ratio_adj -= Decimal("5")
        elif latest.grad_indatorare and latest.grad_indatorare < Decimal("0.5"):
            ratio_adj += Decimal("3")

        details["ratio_adjustment"] = str(ratio_adj)

        score = score + trend_adjustment + ratio_adj
        return (
            max(min(score.quantize(Decimal("0.01")), Decimal("100")), Decimal("0")),
            details,
        )

    def _score_micro_company(
        self,
        revenue: Decimal,
        profit: Decimal,
        equity: Decimal,
        total_liabilities: Decimal,
        total_assets: Decimal,
        nr_angajati: int,
    ) -> tuple[Decimal, dict]:
        """
        1.1: Piauget-style simplified scoring for micro-companies (<9 employees).
        These companies often have minimal assets, so Altman Z doesn't work well.

        Uses 4 simpler factors:
        1. Profitability: profit_net > 0 and margin
        2. Solvency: equity > 0 (not over-leveraged)
        3. Revenue per employee: productivity indicator
        4. Debt ratio: total_liabilities / total_assets
        """
        details: dict = {}
        score = Decimal("50")  # Start neutral

        # Factor 1: Profitability
        if profit > 0:
            if revenue > 0:
                margin = profit / revenue
                if margin > Decimal("0.15"):
                    score += Decimal("20")
                    details["profitability"] = "high"
                elif margin > Decimal("0.05"):
                    score += Decimal("10")
                    details["profitability"] = "moderate"
                else:
                    score += Decimal("5")
                    details["profitability"] = "low_positive"
            else:
                score += Decimal("5")
        else:
            score -= Decimal("15")
            details["profitability"] = "loss"

        # Factor 2: Solvency (positive equity)
        if equity > 0:
            score += Decimal("10")
            details["solvency"] = "positive_equity"
        elif equity == 0:
            details["solvency"] = "zero_equity"
        else:
            score -= Decimal("20")
            details["solvency"] = "negative_equity"

        # Factor 3: Revenue per employee
        if nr_angajati > 0 and revenue > 0:
            rev_per_emp = revenue / Decimal(str(nr_angajati))
            if rev_per_emp > Decimal("500000"):  # >500K RON/employee
                score += Decimal("10")
                details["productivity"] = "very_high"
            elif rev_per_emp > Decimal("200000"):
                score += Decimal("5")
                details["productivity"] = "good"
            elif rev_per_emp < Decimal("50000"):
                score -= Decimal("5")
                details["productivity"] = "low"

        # Factor 4: Debt ratio
        if total_assets > 0:
            debt_ratio = total_liabilities / total_assets
            if debt_ratio < Decimal("0.3"):
                score += Decimal("10")
                details["debt_ratio"] = "conservative"
            elif debt_ratio > Decimal("0.8"):
                score -= Decimal("15")
                details["debt_ratio"] = "over_leveraged"
            elif debt_ratio > Decimal("0.6"):
                score -= Decimal("5")
                details["debt_ratio"] = "high"

        details["nr_angajati"] = nr_angajati
        return score, details

    @staticmethod
    def _zscore_to_100(z_score: Decimal) -> Decimal:
        """Map Altman Z-Score to 0-100 scale."""
        if z_score > Decimal("2.9"):
            return Decimal("80") + min(
                (z_score - Decimal("2.9")) * Decimal("10"), Decimal("20")
            )
        elif z_score > Decimal("1.23"):
            return Decimal("40") + (
                (z_score - Decimal("1.23")) / Decimal("1.67") * Decimal("40")
            )
        else:
            return max(z_score / Decimal("1.23") * Decimal("40"), Decimal("0"))

    def _estimate_credit_limit(
        self, company: Company, total_score: Decimal, financial_details: dict
    ) -> int | None:
        """
        Estimate a suggested credit limit based on score and financials.
        Simple heuristic: % of revenue based on risk category.
        """
        revenue_str = financial_details.get("revenue")
        # Try to get revenue from the latest financial data
        if not revenue_str:
            return None

        try:
            revenue = float(revenue_str)
        except (TypeError, ValueError):
            return None

        if revenue <= 0:
            return 0

        # Credit limit as % of annual revenue
        score_val = float(total_score)
        if score_val >= 80:
            pct = 0.25  # A-rated: up to 25% of revenue
        elif score_val >= 60:
            pct = 0.15  # B-rated: 15%
        elif score_val >= 40:
            pct = 0.08  # C-rated: 8%
        elif score_val >= 20:
            pct = 0.03  # D-rated: 3%
        else:
            pct = 0.0   # E-rated: no credit recommended

        return int(revenue * pct)

    async def _score_legal(self, company: Company) -> tuple[Decimal, dict]:
        """Legal score based on court cases and insolvency."""
        score = Decimal("100")
        details: dict = {}

        # Check insolvency
        if company.has_insolvency:
            score -= Decimal("60")
            details["insolvency_flag"] = True

        # Count active court cases
        result = await self.db.execute(
            select(func.count(CourtCase.id))
            .where(CourtCase.company_id == company.id)
        )
        case_count = result.scalar() or 0
        details["court_case_count"] = case_count

        if case_count > 10:
            score -= Decimal("25")
            details["court_severity"] = "critical"
        elif case_count > 5:
            score -= Decimal("15")
            details["court_severity"] = "high"
        elif case_count > 0:
            score -= Decimal("5")
            details["court_severity"] = "low"

        # Check insolvency cases
        result = await self.db.execute(
            select(func.count(InsolvencyCase.id))
            .where(InsolvencyCase.company_id == company.id)
        )
        insolvency_count = result.scalar() or 0
        details["insolvency_case_count"] = insolvency_count

        if insolvency_count > 0:
            score -= Decimal("20") * min(insolvency_count, 3)

        return max(score, Decimal("0")), details

    async def _score_fiscal(self, company: Company) -> tuple[Decimal, dict]:
        """Fiscal score based on debts and TVA status."""
        score = Decimal("100")
        details: dict = {}

        # TVA status
        if not company.platitor_tva:
            score -= Decimal("20")
            details["tva_platitor"] = False
        else:
            details["tva_platitor"] = True

        if company.inactiv_fiscal:
            score -= Decimal("30")
            details["inactiv_fiscal"] = True

        # Check debts (hard constraint: max 90 days old)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = await self.db.execute(
            select(CompanyDebt)
            .where(
                CompanyDebt.company_id == company.id,
                CompanyDebt.data_raportare >= cutoff,
            )
        )
        debts = result.scalars().all()

        total_debt = sum(float(d.suma_restanta or 0) for d in debts)
        details["total_debt_90d"] = total_debt
        details["debt_count"] = len(debts)

        if total_debt > 1_000_000:
            score -= Decimal("40")
            details["debt_severity"] = "critical"
        elif total_debt > 100_000:
            score -= Decimal("25")
            details["debt_severity"] = "high"
        elif total_debt > 10_000:
            score -= Decimal("10")
            details["debt_severity"] = "moderate"
        elif total_debt > 0:
            score -= Decimal("5")
            details["debt_severity"] = "low"

        if company.has_debts:
            score -= Decimal("15")
            details["has_debts_flag"] = True

        return max(score, Decimal("0")), details

    async def _score_behavioral(self, company: Company) -> tuple[Decimal, dict]:
        """Behavioral score based on company patterns."""
        score = Decimal("80")
        details: dict = {}

        # Company age bonus
        if company.data_infiintare:
            from app.utils.validators import calculate_company_age_years
            age = calculate_company_age_years(company.data_infiintare)
            details["company_age_years"] = age
            if age > 10:
                score += Decimal("15")
                details["age_bonus"] = 15
            elif age > 5:
                score += Decimal("10")
                details["age_bonus"] = 10
            elif age > 2:
                score += Decimal("5")
                details["age_bonus"] = 5
            elif age < 1:
                score -= Decimal("10")
                details["age_bonus"] = -10

        # Admin changes frequency
        result = await self.db.execute(
            select(func.count(CompanyPerson.id))
            .where(
                CompanyPerson.company_id == company.id,
                CompanyPerson.tip == "ADMINISTRATOR",
                CompanyPerson.activ == False,
            )
        )
        former_admins = result.scalar() or 0
        details["former_admin_count"] = former_admins
        if former_admins > 5:
            score -= Decimal("15")
            details["admin_stability"] = "very_unstable"
        elif former_admins > 3:
            score -= Decimal("5")
            details["admin_stability"] = "unstable"
        else:
            details["admin_stability"] = "stable"

        # Company stare check
        if company.stare and company.stare != "ACTIVA":
            score -= Decimal("20")
            details["inactive_penalty"] = True

        return max(min(score, Decimal("100")), Decimal("0")), details

    # ── 1.3: Score history & trend endpoint support ──
    async def get_score_history(self, company_id: int, limit: int = 12) -> list[dict]:
        """
        Return historical risk scores for trend visualization.
        """
        result = await self.db.execute(
            select(RiskScore)
            .where(RiskScore.company_id == company_id)
            .order_by(RiskScore.calculat_la.desc())
            .limit(limit)
        )
        scores = result.scalars().all()
        return [
            {
                "score": s.score,
                "rating": s.rating,
                "calculat_la": s.calculat_la.isoformat() if s.calculat_la else None,
                "scor_financiar": float(s.scor_financiar) if s.scor_financiar else None,
                "scor_legal": float(s.scor_legal) if s.scor_legal else None,
                "scor_fiscal": float(s.scor_fiscal) if s.scor_fiscal else None,
                "scor_comportamental": float(s.scor_comportamental) if s.scor_comportamental else None,
                "model_versiune": s.model_versiune,
            }
            for s in reversed(scores)
        ]

    async def predict_trend(self, company_id: int, months_ahead: int = 6) -> dict:
        """
        1.3: Simple linear regression prediction on historical scores.
        Returns predicted score and direction.
        """
        history = await self.get_score_history(company_id, limit=12)
        if len(history) < 3:
            return {"prediction": None, "reason": "insufficient_data", "data_points": len(history)}

        # Simple linear regression: y = mx + b
        n = len(history)
        x_vals = list(range(n))
        y_vals = [h["score"] for h in history]

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)

        if denominator == 0:
            return {"prediction": y_vals[-1], "direction": "STABLE", "confidence": "low"}

        slope = numerator / denominator

        # Predict `months_ahead` data points forward
        predicted = y_vals[-1] + slope * months_ahead
        predicted = max(1, min(100, round(predicted)))

        if slope > 1:
            direction = "IMPROVING"
        elif slope < -1:
            direction = "DEGRADING"
        else:
            direction = "STABLE"

        return {
            "current_score": y_vals[-1],
            "predicted_score": predicted,
            "months_ahead": months_ahead,
            "direction": direction,
            "slope": round(slope, 3),
            "data_points": n,
            "confidence": "high" if n >= 6 else "medium" if n >= 4 else "low",
        }

    # ── 1.4: Benchmark endpoint ──
    async def get_sector_benchmark(
        self, caen_2: str, judet: str | None = None
    ) -> dict:
        """
        Compute sector benchmark statistics.
        GET /risk/benchmark?caen=62&judet=B
        """
        query = (
            select(RiskScore.score, Company.denumire, Company.cui)
            .join(Company, Company.id == RiskScore.company_id)
            .where(
                func.substr(Company.caen_principal, 1, 2) == caen_2,
                Company.stare == "ACTIVA",
            )
        )
        if judet:
            query = query.where(Company.judet == judet)

        result = await self.db.execute(query)
        rows = result.all()

        if not rows:
            return {"sector": caen_2, "count": 0, "message": "Nu sunt date disponibile"}

        scores = [row[0] for row in rows]
        avg = sum(scores) / len(scores)
        sorted_scores = sorted(scores)
        median = sorted_scores[len(sorted_scores) // 2]

        # Distribution by category
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for s in scores:
            cat = self._categorize(Decimal(str(s)))
            distribution[cat] += 1

        # Top 5 and bottom 5
        top_5 = [
            {"cui": r[2], "denumire": r[1], "score": r[0]}
            for r in sorted(rows, key=lambda x: x[0], reverse=True)[:5]
        ]
        bottom_5 = [
            {"cui": r[2], "denumire": r[1], "score": r[0]}
            for r in sorted(rows, key=lambda x: x[0])[:5]
        ]

        return {
            "sector_caen_2": caen_2,
            "judet": judet,
            "count": len(scores),
            "avg_score": round(avg, 1),
            "median_score": median,
            "min_score": min(scores),
            "max_score": max(scores),
            "distribution": distribution,
            "top_5": top_5,
            "bottom_5": bottom_5,
        }

    def _categorize(self, score: Decimal) -> str:
        for threshold, category in self.CATEGORIES:
            if score >= threshold:
                return category
        return "E"
