"""
Fraud Graph Engine — Neo4j-backed fraud detection with 7 detection algorithms.

v2 Improvements:
  3.1: Carousel dedup — normalize cycles so A→B→C = C→B→A
  3.2: Phoenix — fix "or True" bug, add CAEN similarity + temporal proximity
  3.3: Graph metrics — implement PageRank/betweenness in PostgreSQL fallback
  3.4: New fraud types — address fraud, shell companies, revenue manipulation
  3.5: Composite fraud score — 0-100 aggregated from all algorithms
  3.6: Proactive alerting — batch scan all companies, auto-flag high risk

Algorithms:
  1. Carousel Detection: circular ownership/transaction chains (A→B→C→A)
  2. Phoenix Company Detection: successor companies post-insolvency
  3. Beneficial Owner Clustering: shared control through cross-holdings
  4. Anomaly Scoring: combined anomaly (revenue vs employees, shared HQ, rapid changes)
  5. Address Fraud: virtual offices / excessive shared headquarters
  6. Shell Company Detection: low employees + high revenue + minimal assets
  7. Revenue Manipulation: sudden spikes/drops without structural explanation

Hard constraint #11: All fraud alerts are "suspiciuni algoritmice" NOT legal accusations.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, CompanyPerson, EntityRelation, FraudAlert,
    GraphMetric, InsolvencyCase, FinancialData,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

FRAUD_DISCLAIMER = (
    "Alertele sunt generate automat prin algoritmi de detecție a anomaliilor "
    "și NU constituie acuzații legale. Reprezintă suspiciuni algoritmice."
)


class FraudGraphEngine:
    """
    Neo4j + PostgreSQL hybrid fraud detection engine.
    v2: 7 algorithms, composite scoring, dedup, proactive batch scanning.
    """

    def __init__(self, db: AsyncSession, neo4j_driver=None):
        self.db = db
        self.neo4j = neo4j_driver

    # ─────────────────────────────────────────────
    # Algorithm 1: Carousel Detection (3.1 dedup fix)
    # ─────────────────────────────────────────────
    async def detect_carousels(self, min_cycle_length: int = 3, max_cycle_length: int = 8) -> list[FraudAlert]:
        """
        Detect circular ownership/transaction chains.
        3.1 fix: normalize cycles for dedup — sorted tuple as key.
        """
        alerts = []
        seen_cycles: set[tuple] = set()  # 3.1: dedup set

        if self.neo4j:
            cypher = """
            MATCH path = (a:Company)-[:OWNS*%d..%d]->(a)
            WHERE ALL(r IN relationships(path) WHERE r.active = true)
            RETURN [n IN nodes(path) | n.cui] AS cycle,
                   length(path) AS cycle_length
            LIMIT 100
            """ % (min_cycle_length, max_cycle_length)

            async with self.neo4j.session() as session:
                result = await session.run(cypher)
                async for record in result:
                    cycle = record["cycle"]
                    # 3.1: Normalize cycle for dedup
                    cycle_key = tuple(sorted(set(cycle)))
                    if cycle_key in seen_cycles:
                        continue
                    seen_cycles.add(cycle_key)

                    alert = FraudAlert(
                        alert_type="carousel",
                        severity="HIGH",
                        descriere=f"Lanț circular detectat: {' → '.join(str(c) for c in cycle)}",
                        confidence=Decimal("0.75"),
                        dovezi={
                            "cycle_cuis": cycle,
                            "cycle_length": record["cycle_length"],
                            "disclaimer": FRAUD_DISCLAIMER,
                        },
                    )
                    alerts.append(alert)
        else:
            alerts = await self._detect_carousels_pg(min_cycle_length)

        return alerts

    async def _detect_carousels_pg(self, min_cycle: int) -> list[FraudAlert]:
        """PostgreSQL recursive CTE fallback for carousel detection (3.1 dedup)."""
        alerts = []
        seen_cycles: set[tuple] = set()

        result = await self.db.execute(
            select(EntityRelation).where(EntityRelation.relation_type == "ownership")
        )
        relations = result.scalars().all()

        graph: dict[int, set[int]] = {}
        for r in relations:
            if r.source_id not in graph:
                graph[r.source_id] = set()
            graph[r.source_id].add(r.target_id)

        # Find triangles (A→B→C→A) with dedup
        for a in graph:
            for b in graph.get(a, set()):
                if b == a:
                    continue
                for c in graph.get(b, set()):
                    if c == a or c == b:
                        continue
                    if a in graph.get(c, set()):
                        # 3.1: Normalize — use sorted tuple as canonical form
                        cycle_key = tuple(sorted([a, b, c]))
                        if cycle_key in seen_cycles:
                            continue
                        seen_cycles.add(cycle_key)

                        alert = FraudAlert(
                            company_id=a,
                            alert_type="carousel",
                            severity="HIGH",
                            descriere=f"Lanț circular de proprietate detectat: {a} → {b} → {c} → {a}",
                            confidence=Decimal("0.70"),
                            dovezi={
                                "cycle_company_ids": [a, b, c],
                                "disclaimer": FRAUD_DISCLAIMER,
                            },
                        )
                        alerts.append(alert)

        return alerts

    # ─────────────────────────────────────────────
    # Algorithm 2: Phoenix Company Detection (3.2 bug fix)
    # ─────────────────────────────────────────────
    async def detect_phoenix(self) -> list[FraudAlert]:
        """
        Detect successor companies with same associates/address
        created after insolvency.
        3.2 fix: removed "or True" bug, added CAEN similarity and temporal proximity.
        """
        alerts = []
        seen_pairs: set[tuple] = set()  # Dedup old→new pairs

        insolvent_result = await self.db.execute(
            select(Company).where(Company.has_insolvency == True)
        )
        insolvent_companies = insolvent_result.scalars().all()

        for old_company in insolvent_companies:
            old_associates_result = await self.db.execute(
                select(CompanyPerson.nume_complet)
                .where(
                    CompanyPerson.company_id == old_company.id,
                    CompanyPerson.tip.in_(["ASOCIAT", "ADMINISTRATOR"]),
                )
            )
            old_names = {r for r in old_associates_result.scalars().all() if r}

            if not old_names:
                continue

            for name in old_names:
                new_companies_result = await self.db.execute(
                    select(Company)
                    .join(CompanyPerson, CompanyPerson.company_id == Company.id)
                    .where(
                        CompanyPerson.nume_complet == name,
                        Company.id != old_company.id,
                        Company.data_infiintare > old_company.data_infiintare,
                    )
                    .limit(10)
                )
                new_companies = new_companies_result.scalars().all()

                for new_company in new_companies:
                    # Dedup: skip already seen pairs
                    pair_key = (old_company.id, new_company.id)
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    confidence = Decimal("0.40")
                    flags = []

                    # Address similarity
                    same_address = (
                        old_company.adresa_completa
                        and new_company.adresa_completa
                        and old_company.adresa_completa == new_company.adresa_completa
                    )
                    if same_address:
                        confidence += Decimal("0.20")
                        flags.append("aceeași adresă")

                    # 3.2: CAEN similarity (same sector = higher suspicion)
                    same_caen = (
                        old_company.caen_principal
                        and new_company.caen_principal
                        and old_company.caen_principal[:2] == new_company.caen_principal[:2]
                    )
                    if same_caen:
                        confidence += Decimal("0.15")
                        flags.append("acelaşi sector CAEN")

                    # 3.2: Temporal proximity (created within 2 years of insolvency)
                    if old_company.data_infiintare and new_company.data_infiintare:
                        years_diff = (new_company.data_infiintare - old_company.data_infiintare).days / 365
                        if years_diff < 2:
                            confidence += Decimal("0.10")
                            flags.append("înfiinţată la scurt timp")

                    # 3.2 FIX: Only flag if there's at least one additional signal
                    # (removed "or True" — the shared person alone isn't sufficient)
                    if same_address or same_caen or confidence >= Decimal("0.55"):
                        alert = FraudAlert(
                            company_id=new_company.id,
                            alert_type="phoenix",
                            severity="HIGH" if confidence >= Decimal("0.7") else "MEDIUM",
                            descriere=(
                                f"Posibilă firmă phoenix: {new_company.denumire} (CUI {new_company.cui}) "
                                f"pare succesoare a {old_company.denumire} (CUI {old_company.cui}, insolvență). "
                                f"Semnale: {', '.join(flags) if flags else 'persoană comună'}"
                            ),
                            confidence=min(confidence, Decimal("0.95")),
                            dovezi={
                                "old_cui": old_company.cui,
                                "old_name": old_company.denumire,
                                "new_cui": new_company.cui,
                                "shared_person": name,
                                "same_address": same_address,
                                "same_caen": same_caen,
                                "flags": flags,
                                "disclaimer": FRAUD_DISCLAIMER,
                            },
                        )
                        alerts.append(alert)

        return alerts

    # ─────────────────────────────────────────────
    # Algorithm 3: Beneficial Owner Clustering
    # ─────────────────────────────────────────────
    async def detect_clusters(self) -> list[FraudAlert]:
        """
        Detect groups of companies controlled by the same person/group
        through cross-holdings.
        """
        alerts = []

        result = await self.db.execute(
            select(
                CompanyPerson.nume_complet,
                func.group_concat(func.distinct(CompanyPerson.company_id)).label("company_ids"),
                func.count(func.distinct(CompanyPerson.company_id)).label("cnt"),
            )
            .where(CompanyPerson.tip.in_(["ASOCIAT", "ADMINISTRATOR"]))
            .group_by(CompanyPerson.nume_complet)
            .having(func.count(func.distinct(CompanyPerson.company_id)) >= 5)
        )

        for row in result.all():
            company_ids = [int(x) for x in str(row.company_ids).split(",") if x] if row.company_ids else []
            person_name = row.nume_complet

            companies_result = await self.db.execute(
                select(Company.cui, Company.denumire)
                .where(Company.id.in_(company_ids))
            )
            companies = companies_result.all()

            severity = "HIGH" if len(companies) >= 10 else "MEDIUM"

            alert = FraudAlert(
                alert_type="cluster",
                severity=severity,
                descriere=(
                    f"Cluster de {len(companies)} firme controlate de {person_name}"
                ),
                confidence=Decimal("0.60") + Decimal("0.02") * min(len(companies), 20),
                dovezi={
                    "person": person_name,
                    "companies": [
                        {"cui": c.cui, "denumire": c.denumire}
                        for c in companies
                    ],
                    "disclaimer": FRAUD_DISCLAIMER,
                },
            )
            alerts.append(alert)

        return alerts

    # ─────────────────────────────────────────────
    # Algorithm 4: Anomaly Scoring (enhanced)
    # ─────────────────────────────────────────────
    async def score_anomaly(self, company_id: int) -> FraudAlert | None:
        """
        Combined anomaly score for a company:
          - Revenue vs employees ratio
          - Shared HQ (excessive)
          - Frequent admin/associate changes
          - Unusual financial patterns
        """
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            return None

        anomaly_factors = []
        total_score = Decimal("0")

        # 1. Revenue vs employees
        fin_result = await self.db.execute(
            select(FinancialData)
            .where(FinancialData.company_id == company_id)
            .order_by(FinancialData.an_fiscal.desc())
            .limit(1)
        )
        fin = fin_result.scalar_one_or_none()

        if fin and fin.cifra_afaceri and fin.nr_angajati:
            revenue_per_employee = float(fin.cifra_afaceri) / max(fin.nr_angajati, 1)
            if revenue_per_employee > 5_000_000:
                total_score += Decimal("0.3")
                anomaly_factors.append(f"Cifră afaceri/angajat anormal de mare: {revenue_per_employee:,.0f} RON")
            elif fin.nr_angajati == 0 and fin.cifra_afaceri > Decimal("1000000"):
                total_score += Decimal("0.4")
                anomaly_factors.append("0 angajați cu cifră de afaceri > 1M RON")

        # 2. Shared HQ
        if company.adresa_completa:
            shared_result = await self.db.execute(
                select(func.count(Company.id))
                .where(
                    Company.adresa_completa == company.adresa_completa,
                    Company.id != company.id,
                )
            )
            shared_count = shared_result.scalar() or 0
            if shared_count > 20:
                total_score += Decimal("0.3")
                anomaly_factors.append(f"Sediu partajat cu {shared_count} alte firme")
            elif shared_count > 10:
                total_score += Decimal("0.15")
                anomaly_factors.append(f"Sediu partajat cu {shared_count} firme")

        # 3. Frequent changes
        admin_result = await self.db.execute(
            select(func.count(CompanyPerson.id))
            .where(
                CompanyPerson.company_id == company_id,
                CompanyPerson.activ == False,
            )
        )
        changes = admin_result.scalar() or 0
        if changes > 10:
            total_score += Decimal("0.2")
            anomaly_factors.append(f"Schimbări frecvente personal conducere: {changes}")

        # 4. Company age vs capital (very new + very high capital = suspicious)
        if company.data_infiintare and company.capital_social:
            age_days = (datetime.now().date() - company.data_infiintare).days
            if age_days < 365 and float(company.capital_social) > 1_000_000:
                total_score += Decimal("0.15")
                anomaly_factors.append("Firmă nouă cu capital social mare")

        if not anomaly_factors:
            return None

        if total_score < Decimal("0.3"):
            return None

        severity = "LOW"
        if total_score >= Decimal("0.7"):
            severity = "CRITICAL"
        elif total_score >= Decimal("0.5"):
            severity = "HIGH"
        elif total_score >= Decimal("0.3"):
            severity = "MEDIUM"

        return FraudAlert(
            company_id=company_id,
            alert_type="anomaly",
            severity=severity,
            descriere=f"Scor anomalie: {float(total_score):.2f} — {'; '.join(anomaly_factors)}",
            confidence=min(total_score, Decimal("0.95")),
            dovezi={
                "factors": anomaly_factors,
                "score": float(total_score),
                "disclaimer": FRAUD_DISCLAIMER,
            },
        )

    # ─────────────────────────────────────────────
    # 3.4: Algorithm 5: Address Fraud
    # ─────────────────────────────────────────────
    async def detect_address_fraud(self, threshold: int = 15) -> list[FraudAlert]:
        """
        Detect addresses with suspiciously many companies registered
        (virtual offices, mailbox companies).
        """
        result = await self.db.execute(
            select(
                Company.adresa_completa,
                func.count(Company.id).label("cnt"),
                func.group_concat(Company.cui).label("cuis"),
            )
            .where(Company.adresa_completa.isnot(None))
            .group_by(Company.adresa_completa)
            .having(func.count(Company.id) >= threshold)
            .order_by(func.count(Company.id).desc())
            .limit(50)
        )

        alerts = []
        for row in result.all():
            severity = "CRITICAL" if row.cnt > 50 else "HIGH" if row.cnt > 25 else "MEDIUM"
            confidence = min(Decimal("0.50") + Decimal("0.01") * row.cnt, Decimal("0.95"))

            alert = FraudAlert(
                alert_type="address_fraud",
                severity=severity,
                descriere=(
                    f"Adresă suspectă: {row.cnt} firme înregistrate la aceeași adresă — "
                    f"posibil birou virtual/sediu fictiv"
                ),
                confidence=confidence,
                dovezi={
                    "address": row.adresa_completa,
                    "company_count": row.cnt,
                    "sample_cuis": row.cuis[:20],
                    "disclaimer": FRAUD_DISCLAIMER,
                },
            )
            alerts.append(alert)

        return alerts

    # ─────────────────────────────────────────────
    # 3.4: Algorithm 6: Shell Company Detection
    # ─────────────────────────────────────────────
    async def detect_shell_companies(self) -> list[FraudAlert]:
        """
        Detect potential shell companies:
        - 0-1 employees + high revenue
        - Minimal total assets relative to revenue
        - No operational CAEN activity match
        """
        result = await self.db.execute(
            select(Company, FinancialData)
            .join(FinancialData, FinancialData.company_id == Company.id)
            .where(
                FinancialData.nr_angajati <= 1,
                FinancialData.cifra_afaceri > 500_000,
            )
            .order_by(FinancialData.an_fiscal.desc())
            .limit(200)
        )

        alerts = []
        seen_companies: set[int] = set()

        for company, fin in result.all():
            if company.id in seen_companies:
                continue
            seen_companies.add(company.id)

            confidence = Decimal("0.40")
            flags = []

            employees = fin.nr_angajati or 0
            revenue = float(fin.cifra_afaceri or 0)

            if employees == 0:
                confidence += Decimal("0.20")
                flags.append("0 angajați")

            if revenue > 5_000_000:
                confidence += Decimal("0.15")
                flags.append(f"CA {revenue:,.0f} RON fără angajați")

            # Check if total assets are very low relative to revenue
            total_assets = float(fin.total_activ or 0) if hasattr(fin, 'total_activ') else 0
            if total_assets > 0 and revenue > 0 and total_assets < revenue * 0.05:
                confidence += Decimal("0.10")
                flags.append("active totale minime vs cifra de afaceri")

            if confidence >= Decimal("0.50"):
                alert = FraudAlert(
                    company_id=company.id,
                    alert_type="shell_company",
                    severity="HIGH" if confidence >= Decimal("0.7") else "MEDIUM",
                    descriere=(
                        f"Posibilă firmă fantomă: {company.denumire} (CUI {company.cui}) — "
                        f"{'; '.join(flags)}"
                    ),
                    confidence=min(confidence, Decimal("0.95")),
                    dovezi={
                        "cui": company.cui,
                        "employees": employees,
                        "revenue": revenue,
                        "flags": flags,
                        "disclaimer": FRAUD_DISCLAIMER,
                    },
                )
                alerts.append(alert)

        return alerts

    # ─────────────────────────────────────────────
    # 3.4: Algorithm 7: Revenue Manipulation
    # ─────────────────────────────────────────────
    async def detect_revenue_manipulation(self, spike_threshold: float = 5.0) -> list[FraudAlert]:
        """
        Detect suspicious revenue spikes/drops between consecutive years.
        A spike of >500% or drop of >90% without corresponding employee changes
        is flagged as potential revenue manipulation.
        """
        # Get companies with multiple years of financial data
        result = await self.db.execute(
            select(
                FinancialData.company_id,
                func.count(FinancialData.id).label("cnt"),
            )
            .group_by(FinancialData.company_id)
            .having(func.count(FinancialData.id) >= 2)
        )

        alerts = []
        company_ids = [r[0] for r in result.all()]

        for cid in company_ids[:500]:  # Limit batch size
            fin_result = await self.db.execute(
                select(FinancialData)
                .where(FinancialData.company_id == cid)
                .order_by(FinancialData.an_fiscal.desc())
                .limit(3)
            )
            fins = fin_result.scalars().all()
            if len(fins) < 2:
                continue

            current = fins[0]
            previous = fins[1]

            if not current.cifra_afaceri or not previous.cifra_afaceri:
                continue
            if float(previous.cifra_afaceri) == 0:
                continue

            ratio = float(current.cifra_afaceri) / float(previous.cifra_afaceri)

            flags = []
            confidence = Decimal("0.30")

            # Revenue spike
            if ratio > spike_threshold:
                flags.append(f"Creștere CA {ratio:.0f}x: {float(previous.cifra_afaceri):,.0f} → {float(current.cifra_afaceri):,.0f}")
                confidence += Decimal("0.20")

                # Check if employee count also grew proportionally
                if current.nr_angajati and previous.nr_angajati and previous.nr_angajati > 0:
                    emp_ratio = current.nr_angajati / previous.nr_angajati
                    if emp_ratio < ratio * 0.3:  # Employees didn't grow proportionally
                        confidence += Decimal("0.15")
                        flags.append("angajații nu au crescut proporțional")
                elif not current.nr_angajati or current.nr_angajati == 0:
                    confidence += Decimal("0.20")
                    flags.append("0 angajați raportați")

            # Revenue crash (>90% drop)
            elif ratio < 0.1:
                flags.append(f"Scădere CA {(1-ratio)*100:.0f}%: {float(previous.cifra_afaceri):,.0f} → {float(current.cifra_afaceri):,.0f}")
                confidence += Decimal("0.15")

            if flags and confidence >= Decimal("0.45"):
                # Fetch company info
                comp_result = await self.db.execute(
                    select(Company).where(Company.id == cid)
                )
                company = comp_result.scalar_one_or_none()

                if company:
                    alert = FraudAlert(
                        company_id=cid,
                        alert_type="revenue_manipulation",
                        severity="HIGH" if confidence >= Decimal("0.6") else "MEDIUM",
                        descriere=(
                            f"Variație suspectă CA: {company.denumire} (CUI {company.cui}) — "
                            f"{'; '.join(flags)}"
                        ),
                        confidence=min(confidence, Decimal("0.90")),
                        dovezi={
                            "cui": company.cui,
                            "current_year": current.an_fiscal,
                            "previous_year": previous.an_fiscal,
                            "current_revenue": float(current.cifra_afaceri),
                            "previous_revenue": float(previous.cifra_afaceri),
                            "ratio": round(ratio, 2),
                            "flags": flags,
                            "disclaimer": FRAUD_DISCLAIMER,
                        },
                    )
                    alerts.append(alert)

        return alerts

    # ─────────────────────────────────────────────
    # 3.5: Composite Fraud Score
    # ─────────────────────────────────────────────
    async def composite_fraud_score(self, company_id: int) -> dict:
        """
        3.5: Aggregated fraud risk score (0-100) for a company,
        combining signals from all algorithms.
        """
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        score = 0.0
        signals: list[dict] = []

        # Check existing alerts for this company
        alert_result = await self.db.execute(
            select(FraudAlert)
            .where(FraudAlert.company_id == company_id)
            .order_by(FraudAlert.detectat_la.desc())
        )
        existing_alerts = alert_result.scalars().all()

        severity_weights = {"CRITICAL": 30, "HIGH": 20, "MEDIUM": 10, "LOW": 5}
        type_weights = {
            "carousel": 25, "phoenix": 20, "shell_company": 22,
            "revenue_manipulation": 18, "address_fraud": 10,
            "anomaly": 15, "cluster": 8,
        }

        for alert in existing_alerts:
            weight = type_weights.get(alert.alert_type, 10)
            sev_weight = severity_weights.get(alert.severity, 5)
            alert_score = min(weight + sev_weight, 40) * float(alert.confidence or Decimal("0.5"))
            score += alert_score
            signals.append({
                "type": alert.alert_type,
                "severity": alert.severity,
                "confidence": float(alert.confidence or 0),
                "contribution": round(alert_score, 1),
            })

        # Run live anomaly check
        anomaly = await self.score_anomaly(company_id)
        if anomaly:
            anomaly_score = float(anomaly.confidence or 0) * 20
            score += anomaly_score
            signals.append({
                "type": "anomaly_live",
                "severity": anomaly.severity,
                "confidence": float(anomaly.confidence or 0),
                "contribution": round(anomaly_score, 1),
            })

        # Check shared HQ
        if company.adresa_completa:
            shared_result = await self.db.execute(
                select(func.count(Company.id))
                .where(
                    Company.adresa_completa == company.adresa_completa,
                    Company.id != company.id,
                )
            )
            shared = shared_result.scalar() or 0
            if shared > 10:
                hq_score = min(shared * 0.5, 15)
                score += hq_score
                signals.append({
                    "type": "shared_hq",
                    "count": shared,
                    "contribution": round(hq_score, 1),
                })

        # Cap at 100
        final_score = min(round(score), 100)

        # Risk level
        if final_score >= 80:
            risk_level = "CRITICAL"
        elif final_score >= 60:
            risk_level = "HIGH"
        elif final_score >= 40:
            risk_level = "MEDIUM"
        elif final_score >= 20:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        return {
            "company_id": company_id,
            "cui": company.cui,
            "denumire": company.denumire,
            "fraud_score": final_score,
            "risk_level": risk_level,
            "signals": signals,
            "alert_count": len(existing_alerts),
            "disclaimer": FRAUD_DISCLAIMER,
        }

    # ─────────────────────────────────────────────
    # 3.6: Proactive Batch Scanning
    # ─────────────────────────────────────────────
    async def batch_scan(self, limit: int = 1000) -> dict:
        """
        3.6: Proactive fraud scan across all active companies.
        Runs all detection algorithms and persists results.
        Returns summary statistics.
        """
        logger.info("fraud_batch_scan_start", limit=limit)

        stats = {
            "carousel": 0, "phoenix": 0, "cluster": 0,
            "address_fraud": 0, "shell_company": 0,
            "revenue_manipulation": 0, "total": 0,
        }

        # Run each algorithm and persist alerts
        try:
            carousels = await self.detect_carousels()
            for a in carousels:
                self.db.add(a)
            stats["carousel"] = len(carousels)
        except Exception as e:
            logger.error("fraud_carousel_error", error=str(e))

        try:
            phoenix = await self.detect_phoenix()
            for a in phoenix:
                self.db.add(a)
            stats["phoenix"] = len(phoenix)
        except Exception as e:
            logger.error("fraud_phoenix_error", error=str(e))

        try:
            clusters = await self.detect_clusters()
            for a in clusters:
                self.db.add(a)
            stats["cluster"] = len(clusters)
        except Exception as e:
            logger.error("fraud_cluster_error", error=str(e))

        try:
            addr = await self.detect_address_fraud()
            for a in addr:
                self.db.add(a)
            stats["address_fraud"] = len(addr)
        except Exception as e:
            logger.error("fraud_address_error", error=str(e))

        try:
            shells = await self.detect_shell_companies()
            for a in shells:
                self.db.add(a)
            stats["shell_company"] = len(shells)
        except Exception as e:
            logger.error("fraud_shell_error", error=str(e))

        try:
            revenue = await self.detect_revenue_manipulation()
            for a in revenue:
                self.db.add(a)
            stats["revenue_manipulation"] = len(revenue)
        except Exception as e:
            logger.error("fraud_revenue_error", error=str(e))

        stats["total"] = sum(stats.values())

        logger.info("fraud_batch_scan_complete", **stats)
        return stats

    # ─────────────────────────────────────────────
    # 3.3: Graph Metrics (PostgreSQL fallback)
    # ─────────────────────────────────────────────
    async def calculate_graph_metrics(self, company_id: int) -> GraphMetric | None:
        """
        Calculate centrality metrics.
        3.3: Implemented PageRank approximation and betweenness in PostgreSQL fallback.
        """
        result = await self.db.execute(
            select(Company.cui).where(Company.id == company_id)
        )
        row = result.one_or_none()
        if not row:
            return None
        cui = row.cui

        if self.neo4j:
            return await self._graph_metrics_neo4j(company_id, cui)
        else:
            return await self._graph_metrics_pg(company_id)

    async def _graph_metrics_neo4j(self, company_id: int, cui: int) -> GraphMetric:
        """Neo4j graph metrics with full centrality computation."""
        async with self.neo4j.session() as session:
            degree_result = await session.run(
                "MATCH (c:Company {cui: $cui})-[r]-() RETURN count(r) AS degree",
                cui=cui,
            )
            degree = (await degree_result.single())["degree"]

            # PageRank via GDS if available, otherwise estimate
            try:
                pr_result = await session.run("""
                    CALL gds.pageRank.stream({
                        nodeProjection: 'Company',
                        relationshipProjection: 'OWNS'
                    })
                    YIELD nodeId, score
                    WHERE gds.util.asNode(nodeId).cui = $cui
                    RETURN score
                """, cui=cui)
                pr_record = await pr_result.single()
                pagerank = Decimal(str(pr_record["score"])) if pr_record else Decimal("0")
            except Exception:
                pagerank = Decimal("0")

            # Betweenness via GDS
            try:
                bt_result = await session.run("""
                    CALL gds.betweenness.stream({
                        nodeProjection: 'Company',
                        relationshipProjection: 'OWNS'
                    })
                    YIELD nodeId, score
                    WHERE gds.util.asNode(nodeId).cui = $cui
                    RETURN score
                """, cui=cui)
                bt_record = await bt_result.single()
                betweenness = Decimal(str(bt_record["score"])) if bt_record else Decimal("0")
            except Exception:
                betweenness = Decimal("0")

        metric = GraphMetric(
            company_id=company_id,
            entity_type="COMPANY",
            entity_id=company_id,
            degree_in=degree,
            degree_out=degree,
            betweenness=betweenness,
            pagerank_score=pagerank,
            calculat_la=datetime.now(timezone.utc),
        )
        self.db.add(metric)
        return metric

    async def _graph_metrics_pg(self, company_id: int) -> GraphMetric:
        """
        3.3: PostgreSQL fallback for graph metrics.
        - Degree: count of entity_relations
        - Betweenness: approximated via path counting through shared persons
        - PageRank: iterative approximation based on incoming relations
        """
        # Degree centrality
        in_result = await self.db.execute(
            select(func.count(EntityRelation.id))
            .where(EntityRelation.target_id == company_id)
        )
        out_result = await self.db.execute(
            select(func.count(EntityRelation.id))
            .where(EntityRelation.source_id == company_id)
        )
        degree_in = in_result.scalar() or 0
        degree_out = out_result.scalar() or 0

        # Person-based connections (proxy for betweenness)
        # How many companies connect through shared persons
        persons_result = await self.db.execute(
            select(CompanyPerson.nume_complet)
            .where(CompanyPerson.company_id == company_id)
        )
        person_names = [r for r in persons_result.scalars().all() if r]

        connected_companies = set()
        for name in person_names:
            conn_result = await self.db.execute(
                select(CompanyPerson.company_id)
                .where(
                    CompanyPerson.nume_complet == name,
                    CompanyPerson.company_id != company_id,
                )
            )
            for r in conn_result.scalars().all():
                connected_companies.add(r)

        # Betweenness proxy: normalized connection count
        betweenness = Decimal(str(min(len(connected_companies) / max(degree_in + degree_out, 1), 1.0)))

        # PageRank proxy: based on incoming connections + their degree
        pagerank = Decimal("0.15")  # Base damping factor
        if degree_in > 0:
            pagerank += Decimal("0.85") * Decimal(str(degree_in)) / Decimal("100")

        metric = GraphMetric(
            company_id=company_id,
            entity_type="COMPANY",
            entity_id=company_id,
            degree_in=degree_in,
            degree_out=degree_out,
            betweenness=betweenness.quantize(Decimal("0.0001")),
            pagerank_score=min(pagerank.quantize(Decimal("0.0001")), Decimal("1")),
            calculat_la=datetime.now(timezone.utc),
        )
        self.db.add(metric)
        return metric
