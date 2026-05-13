"""
Fraud Graph endpoints — Neo4j-backed fraud detection.
Hard constraint #11: All fraud alerts marked as "algorithmic suspicion".

v2 Endpoints:
  - GET  /{cui}/profile         → fraud profile
  - GET  /{cui}/alerts          → fraud alerts
  - GET  /{cui}/graph           → ownership graph
  - GET  /{cui}/composite-score → composite fraud score (3.5)
  - POST /scan/batch            → batch scan all companies (3.6)
  - GET  /detection/algorithms  → list algorithms
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role, TokenPayload
from app.models.models import Company, FraudAlert, EntityRelation, GraphMetric
from app.schemas.schemas import FraudAlertSchema, FraudProfileSchema
from app.services.fraud_graph import FraudGraphEngine

router = APIRouter()

FRAUD_DISCLAIMER = (
    "Alertele de fraudă sunt generate automat prin algoritmi de detecție a anomaliilor "
    "și NU constituie acuzații legale. Reprezintă suspiciuni algoritmice care necesită "
    "verificare manuală de către specialiști."
)


@router.get("/{cui}/profile")
async def get_fraud_profile(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get fraud profile including alerts, graph metrics, and entity relations.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get alerts
    alerts_result = await db.execute(
        select(FraudAlert)
        .where(FraudAlert.company_id == company.id)
        .order_by(FraudAlert.detectat_la.desc())
        .limit(20)
    )
    alerts = alerts_result.scalars().all()

    # Get graph metrics
    metrics_result = await db.execute(
        select(GraphMetric)
        .where(
            (GraphMetric.entity_type == "company") &
            (GraphMetric.entity_id == company.id)
        )
        .order_by(GraphMetric.calculat_la.desc())
        .limit(1)
    )
    metrics = metrics_result.scalar_one_or_none()

    # Get related entities
    relations_result = await db.execute(
        select(EntityRelation)
        .where(
            (EntityRelation.source_id == company.id) |
            (EntityRelation.target_id == company.id)
        )
        .limit(50)
    )
    relations = relations_result.scalars().all()

    # Compute anomaly score from alert severity distribution
    anomaly_score = 0.0
    for a in alerts:
        sev = (a.severity or "").upper()
        if sev == "CRITICAL":
            anomaly_score += 25
        elif sev == "HIGH":
            anomaly_score += 15
        elif sev == "MEDIUM":
            anomaly_score += 8
        elif sev == "LOW":
            anomaly_score += 3
    anomaly_score = min(anomaly_score, 100.0)

    return {
        "company_cui": company.cui,
        "company_name": company.denumire,
        "disclaimer": FRAUD_DISCLAIMER,
        "anomaly_score": anomaly_score,
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "descriere": a.descriere,
                "confidence": float(a.confidence) if a.confidence else None,
                "status": a.status,
                "detectat_la": a.detectat_la,
            }
            for a in alerts
        ],
        "graph_metrics": {
            "degree_in": float(metrics.degree_in) if metrics and metrics.degree_in else None,
            "degree_out": float(metrics.degree_out) if metrics and metrics.degree_out else None,
            "betweenness": float(metrics.betweenness) if metrics and metrics.betweenness else None,
            "pagerank_score": float(metrics.pagerank_score) if metrics and metrics.pagerank_score else None,
            "community_id": metrics.community_id if metrics else None,
        } if metrics else None,
        "graph_summary": {
            "nodes": len(set(str(r.source_id) for r in relations) | set(str(r.target_id) for r in relations) | {str(company.id)}),
            "edges": len(relations),
        },
        "related_entities": [
            {
                "source_id": str(r.source_id),
                "target_id": str(r.target_id),
                "relation_type": r.relation_type,
                "sursa": r.sursa,
            }
            for r in relations
        ],
    }


@router.get("/{cui}/alerts")
async def get_fraud_alerts(
    cui: int,
    severity: Optional[str] = Query(default=None, description="low, medium, high, critical"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get fraud alerts for a company.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = select(FraudAlert).where(FraudAlert.company_id == company.id)
    if severity:
        query = query.where(FraudAlert.severity == severity)

    result = await db.execute(query.order_by(FraudAlert.detectat_la.desc()).limit(50))
    alerts = result.scalars().all()

    return {
        "disclaimer": FRAUD_DISCLAIMER,
        "alerts": [
            {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "descriere": a.descriere,
                "confidence": float(a.confidence) if a.confidence else None,
                "dovezi": a.dovezi,
                "detectat_la": a.detectat_la,
            }
            for a in alerts
        ],
    }


@router.get("/{cui}/graph")
async def get_ownership_graph(
    cui: int,
    depth: int = Query(default=2, le=5),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Get ownership/relationship graph data for visualization.
    Uses Neo4j for deep traversal, falls back to PostgreSQL relations.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get direct relations from PostgreSQL
    relations_result = await db.execute(
        select(EntityRelation)
        .where(
            (EntityRelation.source_id == company.id) |
            (EntityRelation.target_id == company.id)
        )
    )
    relations = relations_result.scalars().all()

    # Build nodes and edges for graph visualization
    node_ids = set()
    node_ids.add(company.id)
    edges = []

    for r in relations:
        node_ids.add(r.source_id)
        node_ids.add(r.target_id)
        edges.append({
            "source": r.source_id,
            "target": r.target_id,
            "type": r.relation_type,
            "relationship": r.relation_type,
            "label": r.relation_type,
            "suspicious": r.relation_type in ("BENEFICIAR_REAL", "ACTIONAR_INDIRECT"),
            "sursa": r.sursa,
        })

    # Fetch node details
    if node_ids:
        nodes_result = await db.execute(
            select(Company.id, Company.cui, Company.denumire, Company.stare)
            .where(Company.id.in_(node_ids))
        )
        nodes = [
            {
                "id": n.id,
                "cui": n.cui,
                "label": n.denumire,
                "stare": n.stare,
                "is_center": n.id == company.id,
            }
            for n in nodes_result.all()
        ]
    else:
        nodes = []

    return {
        "center_cui": cui,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/detection/algorithms")
async def list_detection_algorithms(
    user: TokenPayload = Depends(get_current_user),
):
    """
    List available fraud detection algorithms (v2: 7 algorithms).
    """
    return {
        "disclaimer": FRAUD_DISCLAIMER,
        "algorithms": [
            {
                "id": "carousel",
                "name": "Carousel Detection",
                "description": "Detecție lanțuri circulare (A→B→C→A) cu valori similare de tranzacții",
                "min_cycle_length": 3,
            },
            {
                "id": "phoenix",
                "name": "Phoenix Company Detection",
                "description": "Firme succesoare cu aceiași asociați/sediu dar CUI diferit, create după insolvență",
            },
            {
                "id": "clustering",
                "name": "Beneficial Owner Clustering",
                "description": "Detectare grupuri de firme controlate de aceeași persoană/grup prin participații încrucișate",
            },
            {
                "id": "anomaly",
                "name": "Anomaly Scoring",
                "description": "Scor anomalie combinat: cifră afaceri vs angajați, sediu partajat excesiv, schimbări frecvente",
            },
            {
                "id": "address_fraud",
                "name": "Address Fraud Detection",
                "description": "Adrese cu număr excesiv de firme înregistrate (birouri virtuale, sedii fictive)",
            },
            {
                "id": "shell_company",
                "name": "Shell Company Detection",
                "description": "Firme fantomă: 0-1 angajați cu cifre de afaceri mari și active minime",
            },
            {
                "id": "revenue_manipulation",
                "name": "Revenue Manipulation Detection",
                "description": "Variații brusce de cifră de afaceri fără modificări structurale corespunzătoare",
            },
        ],
    }


# ──────────────────────────────────────────────────────────────────
# 3.5: Composite Fraud Score
# ──────────────────────────────────────────────────────────────────

@router.get("/{cui}/composite-score")
async def get_composite_fraud_score(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    3.5: Aggregated fraud risk score (0-100) combining all detection algorithms.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    engine = FraudGraphEngine(db)
    score = await engine.composite_fraud_score(company.id)
    return score


# ──────────────────────────────────────────────────────────────────
# 3.6: Batch Scan
# ──────────────────────────────────────────────────────────────────

@router.post("/scan/batch")
async def batch_fraud_scan(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """
    3.6: Trigger proactive batch fraud scan across all active companies.
    Admin only. Runs all 7 detection algorithms and persists results.
    """
    engine = FraudGraphEngine(db)
    stats = await engine.batch_scan()
    await db.commit()
    return {
        "status": "completed",
        "stats": stats,
        "disclaimer": FRAUD_DISCLAIMER,
    }
