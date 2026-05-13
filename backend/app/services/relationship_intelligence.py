"""
Relationship Intelligence — Branch 14.

Sub-modules:
  14.1  Ultimate Beneficial Owner (UBO) Discovery — Traverse ownership chains
  14.2  Contagion Risk Mapping   — How risk spreads through a network
  14.3  Shared Director Network  — Companies connected by common administrators
  14.4  Group Structure Detection — Corporate group/cluster discovery
  14.5  Relationship Timeline    — Temporal evolution of entity relations
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, or_, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, CompanyPerson, EntityRelation, RiskScore, FinancialData,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum depth for ownership chain traversal
MAX_OWNERSHIP_DEPTH = 10


# ═══════════════════════════════════════════════════════════════════════
# 14.1  ULTIMATE BENEFICIAL OWNER (UBO)
# ═══════════════════════════════════════════════════════════════════════

async def discover_ubo(
    db: AsyncSession,
    company_id: int,
    threshold_pct: float = 25.0,
) -> dict:
    """
    Traverse ownership chains to find Ultimate Beneficial Owners.
    A UBO is any natural person owning (directly or indirectly) >= threshold_pct.

    Algorithm:
      1. Get direct associates with their share percentages
      2. For company-type associates, recursively traverse
      3. Multiply ownership percentages along the chain
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    # Direct associates
    persons_stmt = (
        select(CompanyPerson)
        .where(
            and_(
                CompanyPerson.company_id == company_id,
                CompanyPerson.tip == "ASOCIAT",
                CompanyPerson.activ.is_(True),
            )
        )
    )
    result = await db.execute(persons_stmt)
    direct_associates = result.scalars().all()

    ubos: list[dict] = []
    ownership_chain: list[dict] = []
    visited: set[int] = {company_id}

    for person in direct_associates:
        pct = float(person.procent_parti) if person.procent_parti else 0.0
        chain_entry = {
            "name": person.nume_complet or "Necunoscut",
            "type": "PERSOANA_FIZICA",
            "direct_ownership_pct": round(pct, 3),
            "effective_ownership_pct": round(pct, 3),
            "chain": [company.denumire],
        }
        ownership_chain.append(chain_entry)

        if pct >= threshold_pct:
            ubos.append({
                "name": person.nume_complet or "Necunoscut",
                "ownership_pct": round(pct, 3),
                "type": "DIRECT",
                "chain_length": 1,
                "chain": [company.denumire],
            })

    # Check for company-type ownership through EntityRelation
    rel_stmt = (
        select(EntityRelation)
        .where(
            and_(
                EntityRelation.target_type == "COMPANY",
                EntityRelation.target_id == company_id,
                EntityRelation.relation_type == "OWNERSHIP",
            )
        )
    )
    rel_result = await db.execute(rel_stmt)
    relations = rel_result.scalars().all()

    for rel in relations:
        if rel.source_type == "COMPANY" and rel.source_id not in visited:
            parent_pct = float(rel.weight) if rel.weight else 0.0
            # Recursively trace ownership up
            parent_ubos = await _trace_ownership_up(
                db, rel.source_id, parent_pct, [company.denumire], visited, threshold_pct
            )
            ubos.extend(parent_ubos)

    # Deduplicate UBOs
    seen_names: set[str] = set()
    unique_ubos = []
    for ubo in sorted(ubos, key=lambda x: x["ownership_pct"], reverse=True):
        if ubo["name"] not in seen_names:
            seen_names.add(ubo["name"])
            unique_ubos.append(ubo)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "threshold_pct": threshold_pct,
        "ubos": unique_ubos,
        "direct_associates": [
            {
                "name": p.nume_complet,
                "pct": float(p.procent_parti) if p.procent_parti else 0,
                "type": p.tip,
                "active": p.activ,
            }
            for p in direct_associates
        ],
        "total_associates": len(direct_associates),
        "ubo_count": len(unique_ubos),
    }


async def _trace_ownership_up(
    db: AsyncSession,
    company_id: int,
    accumulated_pct: float,
    chain: list[str],
    visited: set[int],
    threshold: float,
    depth: int = 0,
) -> list[dict]:
    """Recursively trace ownership upward through corporate chains."""
    if depth >= MAX_OWNERSHIP_DEPTH or company_id in visited:
        return []

    visited.add(company_id)
    company = await db.get(Company, company_id)
    if not company:
        return []

    current_chain = chain + [company.denumire]
    ubos = []

    # Check persons owning this company
    persons_stmt = (
        select(CompanyPerson)
        .where(
            and_(
                CompanyPerson.company_id == company_id,
                CompanyPerson.tip == "ASOCIAT",
                CompanyPerson.activ.is_(True),
            )
        )
    )
    result = await db.execute(persons_stmt)
    associates = result.scalars().all()

    for person in associates:
        person_pct = float(person.procent_parti) if person.procent_parti else 0
        effective_pct = (accumulated_pct * person_pct) / 100.0
        if effective_pct >= threshold:
            ubos.append({
                "name": person.nume_complet or "Necunoscut",
                "ownership_pct": round(effective_pct, 3),
                "type": "INDIRECT",
                "chain_length": len(current_chain),
                "chain": current_chain,
            })

    # Continue up
    rel_stmt = (
        select(EntityRelation)
        .where(
            and_(
                EntityRelation.target_type == "COMPANY",
                EntityRelation.target_id == company_id,
                EntityRelation.relation_type == "OWNERSHIP",
            )
        )
    )
    rel_result = await db.execute(rel_stmt)
    parent_rels = rel_result.scalars().all()

    for rel in parent_rels:
        if rel.source_type == "COMPANY" and rel.source_id not in visited:
            parent_pct = float(rel.weight) if rel.weight else 0
            effective_pct = (accumulated_pct * parent_pct) / 100.0
            parent_ubos = await _trace_ownership_up(
                db, rel.source_id, effective_pct, current_chain,
                visited, threshold, depth + 1
            )
            ubos.extend(parent_ubos)

    return ubos


# ═══════════════════════════════════════════════════════════════════════
# 14.2  CONTAGION RISK MAPPING
# ═══════════════════════════════════════════════════════════════════════

async def map_contagion_risk(
    db: AsyncSession,
    company_id: int,
    max_depth: int = 3,
) -> dict:
    """
    Map how risk can spread from a company through its network.
    Uses BFS on EntityRelation to find connected companies,
    then calculates risk exposure for each.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    # BFS through relations
    queue: deque[tuple[int, int]] = deque([(company_id, 0)])
    visited: dict[int, int] = {company_id: 0}
    edges: list[dict] = []

    while queue:
        current_id, depth = queue.popleft()
        if depth >= max_depth:
            continue

        # Get relations from this entity
        rel_stmt = (
            select(EntityRelation)
            .where(
                or_(
                    and_(EntityRelation.source_type == "COMPANY",
                         EntityRelation.source_id == current_id),
                    and_(EntityRelation.target_type == "COMPANY",
                         EntityRelation.target_id == current_id),
                )
            )
        )
        rel_result = await db.execute(rel_stmt)
        relations = rel_result.scalars().all()

        for rel in relations:
            neighbor_id = None
            if rel.source_type == "COMPANY" and rel.source_id == current_id:
                if rel.target_type == "COMPANY":
                    neighbor_id = rel.target_id
            elif rel.target_type == "COMPANY" and rel.target_id == current_id:
                if rel.source_type == "COMPANY":
                    neighbor_id = rel.source_id

            if neighbor_id and neighbor_id not in visited:
                visited[neighbor_id] = depth + 1
                queue.append((neighbor_id, depth + 1))
                edges.append({
                    "source": current_id,
                    "target": neighbor_id,
                    "relation": rel.relation_type,
                    "weight": float(rel.weight) if rel.weight else 1.0,
                })

    # Fetch risk scores for all connected companies
    connected_ids = list(visited.keys())
    risk_stmt = (
        select(RiskScore.company_id, RiskScore.score, RiskScore.rating)
        .where(RiskScore.company_id.in_(connected_ids))
    )
    risk_result = await db.execute(risk_stmt)
    risk_map = {r.company_id: {"score": r.score, "rating": r.rating} for r in risk_result.all()}

    # Fetch company names
    name_stmt = (
        select(Company.id, Company.denumire, Company.cui)
        .where(Company.id.in_(connected_ids))
    )
    name_result = await db.execute(name_stmt)
    name_map = {r.id: {"name": r.denumire, "cui": r.cui} for r in name_result.all()}

    # Build nodes with risk exposure
    nodes = []
    high_risk_count = 0
    for cid, depth in visited.items():
        risk = risk_map.get(cid, {})
        info = name_map.get(cid, {})
        score = risk.get("score", 50)
        if score < 40:
            high_risk_count += 1

        # Contagion weight decays with distance
        contagion_weight = 1.0 / (depth + 1)
        nodes.append({
            "company_id": cid,
            "name": info.get("name", "N/A"),
            "cui": info.get("cui"),
            "depth": depth,
            "risk_score": score,
            "risk_rating": risk.get("rating"),
            "contagion_weight": round(contagion_weight, 4),
        })

    # Aggregate risk
    if nodes:
        weighted_risk = sum(n["risk_score"] * n["contagion_weight"] for n in nodes)
        total_weight = sum(n["contagion_weight"] for n in nodes)
        network_risk = round(weighted_risk / total_weight, 2) if total_weight > 0 else 50
    else:
        network_risk = 50

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "network_risk_score": network_risk,
        "total_connected": len(nodes),
        "high_risk_connected": high_risk_count,
        "max_depth_reached": max(visited.values()) if visited else 0,
        "nodes": sorted(nodes, key=lambda x: x["depth"]),
        "edges": edges,
    }


# ═══════════════════════════════════════════════════════════════════════
# 14.3  SHARED DIRECTOR NETWORK
# ═══════════════════════════════════════════════════════════════════════

async def shared_directors_network(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Find all companies sharing administrators/directors with the target company.
    Returns a network of companies connected by common management.
    """
    # Get directors of target company
    dir_stmt = (
        select(CompanyPerson)
        .where(
            and_(
                CompanyPerson.company_id == company_id,
                CompanyPerson.tip == "ADMINISTRATOR",
                CompanyPerson.activ.is_(True),
            )
        )
    )
    dir_result = await db.execute(dir_stmt)
    directors = dir_result.scalars().all()

    if not directors:
        return {
            "company_id": company_id,
            "shared_directors": [],
            "connected_companies": [],
            "total_connections": 0,
        }

    director_names = [d.nume_complet for d in directors if d.nume_complet]

    # Find other companies with same directors
    if not director_names:
        return {
            "company_id": company_id,
            "shared_directors": [],
            "connected_companies": [],
            "total_connections": 0,
        }

    other_stmt = (
        select(
            CompanyPerson.company_id,
            CompanyPerson.nume_complet,
            CompanyPerson.tip,
            Company.denumire,
            Company.cui,
        )
        .join(Company, Company.id == CompanyPerson.company_id)
        .where(
            and_(
                CompanyPerson.nume_complet.in_(director_names),
                CompanyPerson.company_id != company_id,
                CompanyPerson.activ.is_(True),
            )
        )
    )
    other_result = await db.execute(other_stmt)
    connections = other_result.all()

    # Group by company
    company_map: dict[int, dict] = {}
    for conn in connections:
        cid = conn.company_id
        if cid not in company_map:
            company_map[cid] = {
                "company_id": cid,
                "name": conn.denumire,
                "cui": conn.cui,
                "shared_persons": [],
            }
        company_map[cid]["shared_persons"].append({
            "name": conn.nume_complet,
            "role": conn.tip,
        })

    connected = list(company_map.values())

    # Fetch risk scores for connected companies
    if connected:
        risk_stmt = (
            select(RiskScore.company_id, RiskScore.score, RiskScore.rating)
            .where(RiskScore.company_id.in_([c["company_id"] for c in connected]))
        )
        risk_result = await db.execute(risk_stmt)
        risk_map = {r.company_id: {"score": r.score, "rating": r.rating}
                    for r in risk_result.all()}
        for c in connected:
            risk = risk_map.get(c["company_id"], {})
            c["risk_score"] = risk.get("score")
            c["risk_rating"] = risk.get("rating")
            c["shared_count"] = len(c["shared_persons"])

    return {
        "company_id": company_id,
        "directors": [{"name": d.nume_complet, "since": str(d.data_start) if d.data_start else None}
                      for d in directors],
        "connected_companies": sorted(connected, key=lambda x: x.get("shared_count", 0), reverse=True),
        "total_connections": len(connected),
        "unique_shared_persons": len(set(c["name"] for conn in connections for c in [conn])),
    }


# ═══════════════════════════════════════════════════════════════════════
# 14.4  GROUP STRUCTURE DETECTION
# ═══════════════════════════════════════════════════════════════════════

async def detect_corporate_group(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Detect corporate group structure using union-find on shared ownership + directors.
    Returns group hierarchy with parent/subsidiary relationships.
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    # Collect all related companies via EntityRelation
    related_ids: set[int] = {company_id}
    queue = deque([company_id])
    edges: list[dict] = []

    while queue:
        current = queue.popleft()
        rel_stmt = (
            select(EntityRelation)
            .where(
                or_(
                    and_(EntityRelation.source_type == "COMPANY",
                         EntityRelation.source_id == current),
                    and_(EntityRelation.target_type == "COMPANY",
                         EntityRelation.target_id == current),
                )
            )
        )
        result = await db.execute(rel_stmt)
        rels = result.scalars().all()

        for rel in rels:
            neighbor = None
            if rel.source_type == "COMPANY" and rel.source_id == current and rel.target_type == "COMPANY":
                neighbor = rel.target_id
            elif rel.target_type == "COMPANY" and rel.target_id == current and rel.source_type == "COMPANY":
                neighbor = rel.source_id

            if neighbor and neighbor not in related_ids:
                related_ids.add(neighbor)
                queue.append(neighbor)
                edges.append({
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relation_type,
                    "weight": float(rel.weight) if rel.weight else None,
                })

    # Fetch details for all group members
    if not related_ids:
        return {
            "company_id": company_id,
            "group_members": [],
            "group_size": 1,
        }

    details_stmt = (
        select(
            Company.id, Company.denumire, Company.cui,
            Company.caen_principal, Company.stare,
            Company.data_infiintare,
        )
        .where(Company.id.in_(related_ids))
    )
    details_result = await db.execute(details_stmt)
    members_raw = details_result.all()

    # Fetch financials for size comparison
    fin_stmt = (
        select(
            FinancialData.company_id,
            func.max(FinancialData.cifra_afaceri).label("max_ca"),
            func.max(FinancialData.nr_angajati).label("max_emp"),
        )
        .where(FinancialData.company_id.in_(related_ids))
        .group_by(FinancialData.company_id)
    )
    fin_result = await db.execute(fin_stmt)
    fin_map = {r.company_id: {"ca": r.max_ca, "employees": r.max_emp}
               for r in fin_result.all()}

    members = []
    for m in members_raw:
        fin = fin_map.get(m.id, {})
        members.append({
            "company_id": m.id,
            "name": m.denumire,
            "cui": m.cui,
            "caen": m.caen_principal,
            "stare": m.stare,
            "data_infiintare": str(m.data_infiintare) if m.data_infiintare else None,
            "cifra_afaceri": int(fin["ca"]) if fin.get("ca") else None,
            "nr_angajati": int(fin["employees"]) if fin.get("employees") else None,
            "is_target": m.id == company_id,
        })

    # Sort by CA (largest first = likely parent)
    members.sort(key=lambda x: x.get("cifra_afaceri") or 0, reverse=True)

    # Aggregate group stats
    total_ca = sum(m["cifra_afaceri"] or 0 for m in members)
    total_emp = sum(m["nr_angajati"] or 0 for m in members)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "group_size": len(members),
        "group_members": members,
        "group_edges": edges,
        "group_total_ca": total_ca,
        "group_total_employees": total_emp,
        "probable_parent": members[0] if members else None,
    }


# ═══════════════════════════════════════════════════════════════════════
# 14.5  RELATIONSHIP TIMELINE
# ═══════════════════════════════════════════════════════════════════════

async def relationship_timeline(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """
    Build a timeline of relationship changes for a company:
    - Director/associate changes
    - Ownership changes
    - Entity relations created/ended
    """
    company = await db.get(Company, company_id)
    if not company:
        return {"error": "Firma nu a fost găsită", "company_id": company_id}

    events: list[dict] = []

    # Person changes
    persons_stmt = (
        select(CompanyPerson)
        .where(CompanyPerson.company_id == company_id)
        .order_by(CompanyPerson.data_start.asc().nullslast())
    )
    persons_result = await db.execute(persons_stmt)
    persons = persons_result.scalars().all()

    for p in persons:
        if p.data_start:
            events.append({
                "date": str(p.data_start),
                "type": "PERSON_JOINED",
                "category": p.tip,
                "detail": f"{p.nume_complet or 'Necunoscut'} — {p.tip}",
                "metadata": {
                    "name": p.nume_complet,
                    "role": p.tip,
                    "pct": float(p.procent_parti) if p.procent_parti else None,
                },
            })
        if p.data_sfarsit:
            events.append({
                "date": str(p.data_sfarsit),
                "type": "PERSON_LEFT",
                "category": p.tip,
                "detail": f"{p.nume_complet or 'Necunoscut'} — {p.tip} (ieșire)",
                "metadata": {
                    "name": p.nume_complet,
                    "role": p.tip,
                },
            })

    # Entity relations
    rel_stmt = (
        select(EntityRelation)
        .where(
            or_(
                and_(EntityRelation.source_type == "COMPANY",
                     EntityRelation.source_id == company_id),
                and_(EntityRelation.target_type == "COMPANY",
                     EntityRelation.target_id == company_id),
            )
        )
        .order_by(EntityRelation.valid_from.asc().nullslast())
    )
    rel_result = await db.execute(rel_stmt)
    relations = rel_result.scalars().all()

    for rel in relations:
        if rel.valid_from:
            events.append({
                "date": str(rel.valid_from),
                "type": "RELATION_CREATED",
                "category": rel.relation_type,
                "detail": f"Relație {rel.relation_type} ({rel.source_type}:{rel.source_id} → {rel.target_type}:{rel.target_id})",
                "metadata": {
                    "relation_type": rel.relation_type,
                    "weight": float(rel.weight) if rel.weight else None,
                },
            })
        if rel.valid_to:
            events.append({
                "date": str(rel.valid_to),
                "type": "RELATION_ENDED",
                "category": rel.relation_type,
                "detail": f"Relație {rel.relation_type} încheiată",
                "metadata": {
                    "relation_type": rel.relation_type,
                },
            })

    # Sort by date
    events.sort(key=lambda e: e["date"])

    # Summary stats
    active_associates = sum(1 for p in persons if p.tip == "ASOCIAT" and p.activ)
    active_admins = sum(1 for p in persons if p.tip == "ADMINISTRATOR" and p.activ)

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "events": events,
        "total_events": len(events),
        "active_associates": active_associates,
        "active_administrators": active_admins,
        "total_persons_ever": len(persons),
    }
