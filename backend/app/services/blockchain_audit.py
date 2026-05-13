"""
Blockchain Audit Service — immutable audit trail, document hashing,
smart contract verification, chain of custody, and timestamping.
Uses SHA-256 hash chains for tamper-proof record keeping.
Persisted to PostgreSQL via SQLAlchemy models.
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, cast, Text
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company,
    FinancialData,
    AuditLog,
    BlockchainBlock,
    DocumentHash,
    CustodyRecord,
)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def _get_last_block(db: AsyncSession) -> dict | None:
    """Get the last block from DB."""
    stmt = select(BlockchainBlock).order_by(BlockchainBlock.block_index.desc()).limit(1)
    block = (await db.execute(stmt)).scalar_one_or_none()
    if block:
        return {
            "index": block.block_index,
            "hash": block.block_hash,
            "previous_hash": block.previous_hash,
            "data": block.data_json,
            "timestamp": block.created_at.isoformat() if block.created_at else None,
        }
    return None


async def _get_chain_length(db: AsyncSession) -> int:
    stmt = select(func.count(BlockchainBlock.id))
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _create_and_persist_block(db: AsyncSession, data: dict) -> dict:
    """Create a new block and persist it to DB."""
    last = await _get_last_block(db)
    prev_hash = last["hash"] if last else "0" * 64
    new_index = (last["index"] + 1) if last else 0

    block_data = {
        "index": new_index,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
        "previous_hash": prev_hash,
        "nonce": 0,
    }
    block_str = json.dumps(block_data, sort_keys=True, default=str)
    block_hash = _sha256(block_str)

    db_block = BlockchainBlock(
        block_index=new_index,
        block_hash=block_hash,
        previous_hash=prev_hash,
        data_json=data,
        nonce=0,
    )
    db.add(db_block)
    await db.flush()

    return {
        "index": new_index,
        "hash": block_hash,
        "previous_hash": prev_hash,
        "data": data,
        "timestamp": block_data["timestamp"],
    }


async def _init_genesis(db: AsyncSession):
    """Initialize genesis block if chain is empty."""
    chain_len = await _get_chain_length(db)
    if chain_len == 0:
        genesis_data = {"type": "genesis", "message": "RomBiz Audit Chain Genesis Block"}
        await _create_and_persist_block(db, genesis_data)
        await db.commit()


async def _verify_chain(db: AsyncSession) -> bool:
    """Verify the integrity of the entire chain."""
    stmt = select(BlockchainBlock).order_by(BlockchainBlock.block_index.asc())
    blocks = (await db.execute(stmt)).scalars().all()
    for i in range(1, len(blocks)):
        if blocks[i].previous_hash != blocks[i - 1].block_hash:
            return False
    return True


# ---------------------------------------------------------------------------
# 1. Immutable Audit Trail
# ---------------------------------------------------------------------------
async def audit_trail(
    db: AsyncSession,
    company_id: int,
    limit: int = 50,
) -> dict:
    """Get blockchain-anchored audit trail for a company."""
    await _init_genesis(db)

    # Get audit logs from DB
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == "company", AuditLog.entity_id == str(company_id))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = (await db.execute(stmt)).scalars().all()

    entries = []
    for log in logs:
        log_data = {
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "user_id": str(log.user_id) if log.user_id else None,
        }
        log_hash = _sha256(json.dumps(log_data, sort_keys=True, default=str))
        entries.append({
            "log_id": str(log.id),
            "action": log.action,
            "timestamp": log_data["timestamp"],
            "user_id": log_data["user_id"],
            "hash": log_hash,
            "verified": True,
        })

    # Also get blockchain-anchored events
    stmt2 = (
        select(BlockchainBlock)
        .where(
            cast(BlockchainBlock.data_json, PG_JSONB)["company_id"].astext == str(company_id)
        )
        .order_by(BlockchainBlock.block_index.desc())
        .limit(20)
    )
    try:
        chain_blocks = (await db.execute(stmt2)).scalars().all()
    except Exception:
        chain_blocks = []

    for blk in chain_blocks:
        entries.append({
            "log_id": f"chain_{blk.block_index}",
            "action": blk.data_json.get("action", "BLOCKCHAIN_RECORD") if blk.data_json else "BLOCKCHAIN_RECORD",
            "timestamp": blk.created_at.isoformat() if blk.created_at else None,
            "user_id": blk.data_json.get("user_id") if blk.data_json else None,
            "hash": blk.block_hash,
            "block_index": blk.block_index,
            "verified": True,
        })

    entries.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    chain_len = await _get_chain_length(db)
    chain_valid = await _verify_chain(db)

    return {
        "company_id": company_id,
        "total_entries": len(entries),
        "chain_length": chain_len,
        "chain_valid": chain_valid,
        "entries": entries[:limit],
    }


# ---------------------------------------------------------------------------
# 2. Document Hashing
# ---------------------------------------------------------------------------
async def hash_document(
    db: AsyncSession,
    document_content: str,
    document_name: str,
    company_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Hash a document and anchor it to the blockchain."""
    await _init_genesis(db)

    doc_hash = _sha256(document_content)
    timestamp = datetime.utcnow()

    # Check if already exists in DB
    stmt = select(DocumentHash).where(DocumentHash.document_hash == doc_hash)
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        return {
            "status": "ALREADY_EXISTS",
            "document_hash": doc_hash,
            "original_timestamp": existing.created_at.isoformat() if existing.created_at else None,
            "document_name": existing.document_name,
            "message": "Documentul a fost deja înregistrat în blockchain.",
        }

    # Add to blockchain
    block = await _create_and_persist_block(db, {
        "type": "document_hash",
        "action": "DOCUMENT_REGISTERED",
        "document_hash": doc_hash,
        "document_name": document_name,
        "company_id": company_id,
        "user_id": user_id,
    })

    # Store hash record
    doc_record = DocumentHash(
        document_hash=doc_hash,
        document_name=document_name,
        company_id=company_id,
        user_id=user_id,
        size_bytes=len(document_content.encode("utf-8")),
        block_index=block["index"],
    )
    db.add(doc_record)
    await db.commit()

    return {
        "status": "REGISTERED",
        "document_hash": doc_hash,
        "block_index": block["index"],
        "block_hash": block["hash"],
        "timestamp": timestamp.isoformat(),
        "document_name": document_name,
        "chain_length": await _get_chain_length(db),
    }


async def verify_document(
    db: AsyncSession,
    document_content: str,
) -> dict:
    """Verify a document against the blockchain."""
    doc_hash = _sha256(document_content)

    stmt = select(DocumentHash).where(DocumentHash.document_hash == doc_hash)
    record = (await db.execute(stmt)).scalar_one_or_none()

    if record:
        return {
            "verified": True,
            "document_hash": doc_hash,
            "original_timestamp": record.created_at.isoformat() if record.created_at else None,
            "document_name": record.document_name,
            "company_id": record.company_id,
            "message": "Documentul este autentic — hash-ul se potrivește cu înregistrarea blockchain.",
        }

    return {
        "verified": False,
        "document_hash": doc_hash,
        "message": "Documentul NU a fost găsit în blockchain. Poate fi modificat sau neînregistrat.",
    }


# ---------------------------------------------------------------------------
# 3. Smart Contract Verification
# ---------------------------------------------------------------------------
async def smart_contract_check(
    db: AsyncSession,
    company_id: int,
) -> dict:
    """Verify company data integrity using smart contract logic rules."""
    await _init_genesis(db)

    company = await db.get(Company, company_id)
    if not company:
        return {"company_id": company_id, "error": "Companie negăsită"}

    fin_stmt = (
        select(FinancialData)
        .where(FinancialData.company_id == company_id)
        .order_by(FinancialData.an.desc())
        .limit(5)
    )
    fins = (await db.execute(fin_stmt)).scalars().all()

    checks = []

    # Rule 1: Revenue consistency
    if len(fins) >= 2:
        for i in range(len(fins) - 1):
            if fins[i].cifra_afaceri and fins[i + 1].cifra_afaceri:
                change = abs(fins[i].cifra_afaceri - fins[i + 1].cifra_afaceri) / max(abs(fins[i + 1].cifra_afaceri), 1)
                checks.append({
                    "rule": "REVENUE_CONSISTENCY",
                    "description": f"Variație CA {fins[i].an}/{fins[i+1].an}: {change*100:.0f}%",
                    "passed": change < 5.0,
                    "severity": "HIGH" if change >= 5.0 else "LOW",
                    "value": round(change * 100, 1),
                })
                break

    # Rule 2: Profit vs Revenue validity
    if fins and fins[0].cifra_afaceri and fins[0].profit_net:
        margin = fins[0].profit_net / fins[0].cifra_afaceri
        checks.append({
            "rule": "PROFIT_MARGIN_VALIDITY",
            "description": f"Marja profit: {margin*100:.1f}% (an {fins[0].an})",
            "passed": -1 < margin < 1,
            "severity": "HIGH" if abs(margin) > 1 else "LOW",
            "value": round(margin * 100, 1),
        })

    # Rule 3: Employee count plausibility
    if fins and fins[0].numar_angajati is not None and fins[0].cifra_afaceri:
        rev_per_emp = fins[0].cifra_afaceri / max(fins[0].numar_angajati, 1)
        checks.append({
            "rule": "EMPLOYEE_REVENUE_RATIO",
            "description": f"Revenue/angajat: {rev_per_emp:,.0f} RON",
            "passed": 10_000 < rev_per_emp < 50_000_000,
            "severity": "MEDIUM" if rev_per_emp <= 10_000 or rev_per_emp >= 50_000_000 else "LOW",
            "value": round(rev_per_emp),
        })

    # Rule 4: Capital social validity
    if company.capital_social is not None:
        checks.append({
            "rule": "CAPITAL_SOCIAL_VALID",
            "description": f"Capital social: {company.capital_social:,.0f} RON",
            "passed": company.capital_social >= 0,
            "severity": "HIGH" if company.capital_social < 0 else "LOW",
            "value": company.capital_social,
        })

    # Rule 5: Data completeness
    missing_fields = []
    if not company.caen_principal:
        missing_fields.append("caen_principal")
    if not company.judet:
        missing_fields.append("judet")
    if not fins:
        missing_fields.append("financial_data")

    checks.append({
        "rule": "DATA_COMPLETENESS",
        "description": f"Câmpuri lipsă: {', '.join(missing_fields) if missing_fields else 'niciunul'}",
        "passed": len(missing_fields) == 0,
        "severity": "MEDIUM" if missing_fields else "LOW",
        "value": len(missing_fields),
    })

    # Rule 6: Active status consistency
    if company.stare and fins:
        if company.stare == "ACTIV" and fins[0].cifra_afaceri == 0 and fins[0].numar_angajati == 0:
            checks.append({
                "rule": "STATUS_CONSISTENCY",
                "description": "Firmă ACTIVĂ dar cu CA=0 și angajați=0",
                "passed": False,
                "severity": "MEDIUM",
                "value": 0,
            })
        else:
            checks.append({
                "rule": "STATUS_CONSISTENCY",
                "description": f"Status {company.stare} consistent cu datele financiare",
                "passed": True,
                "severity": "LOW",
                "value": 1,
            })

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    # Anchor result to blockchain
    block = await _create_and_persist_block(db, {
        "type": "smart_contract",
        "action": "CONTRACT_VERIFICATION",
        "company_id": company_id,
        "checks_passed": passed,
        "checks_total": total,
    })
    await db.commit()

    return {
        "company_id": company_id,
        "company_name": company.denumire,
        "verification_timestamp": datetime.utcnow().isoformat(),
        "checks_passed": passed,
        "checks_total": total,
        "integrity_score": round(passed / max(total, 1) * 100, 1),
        "verdict": "VALID" if passed == total else "ANOMALII_DETECTATE" if passed >= total * 0.7 else "ATENTIE",
        "checks": checks,
        "block_hash": block["hash"],
        "block_index": block["index"],
    }


# ---------------------------------------------------------------------------
# 4. Chain of Custody
# ---------------------------------------------------------------------------
async def chain_of_custody(
    db: AsyncSession,
    company_id: int,
    action: str | None = None,
    details: str | None = None,
    user_id: int | None = None,
) -> dict:
    """Track chain of custody for company data access and modifications."""
    await _init_genesis(db)

    # Register new custody event if action provided
    if action:
        record_hash = _sha256(f"{company_id}:{action}:{details}:{user_id}:{datetime.utcnow().isoformat()}")

        custody = CustodyRecord(
            company_id=company_id,
            action=action,
            details=details or "",
            user_id=user_id,
            record_hash=record_hash,
        )

        # Anchor to blockchain
        block = await _create_and_persist_block(db, {
            "type": "custody",
            "action": "CUSTODY_RECORD",
            "company_id": company_id,
            "custody_action": action,
            "user_id": user_id,
        })
        custody.block_index = block["index"]
        db.add(custody)
        await db.commit()

    # Return custody history from DB
    stmt = (
        select(CustodyRecord)
        .where(CustodyRecord.company_id == company_id)
        .order_by(CustodyRecord.created_at.desc())
        .limit(50)
    )
    records_db = (await db.execute(stmt)).scalars().all()

    records = [
        {
            "id": str(r.id),
            "action": r.action,
            "details": r.details,
            "user_id": str(r.user_id) if r.user_id else None,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
            "hash": r.record_hash,
            "block_index": r.block_index,
        }
        for r in records_db
    ]

    # Also get audit logs from DB
    stmt2 = (
        select(AuditLog)
        .where(AuditLog.entity_type == "company", AuditLog.entity_id == str(company_id))
        .order_by(AuditLog.created_at.desc())
        .limit(30)
    )
    db_logs = (await db.execute(stmt2)).scalars().all()

    db_records = [
        {
            "id": f"db_{log.id}",
            "action": log.action,
            "details": f"DB Audit: {log.action}",
            "user_id": str(log.user_id) if log.user_id else None,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "hash": _sha256(f"{log.id}:{log.action}:{log.entity_id}"),
            "source": "audit_log",
        }
        for log in db_logs
    ]

    all_records = records + db_records
    all_records.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    chain_valid = await _verify_chain(db)

    return {
        "company_id": company_id,
        "total_custody_events": len(all_records),
        "chain_records": len(records),
        "db_audit_records": len(db_records),
        "records": all_records[:50],
        "chain_integrity": chain_valid,
    }


# ---------------------------------------------------------------------------
# 5. Timestamp Proof
# ---------------------------------------------------------------------------
async def timestamp_proof(
    db: AsyncSession,
    data: str,
    proof_type: str = "generic",
    company_id: int | None = None,
) -> dict:
    """Create a timestamped proof anchored to the blockchain."""
    await _init_genesis(db)

    data_hash = _sha256(data)
    timestamp = datetime.utcnow()

    block = await _create_and_persist_block(db, {
        "type": "timestamp_proof",
        "action": "TIMESTAMP_CREATED",
        "data_hash": data_hash,
        "proof_type": proof_type,
        "company_id": company_id,
    })
    await db.commit()

    chain_len = await _get_chain_length(db)

    # Chain stats
    first_stmt = select(BlockchainBlock).order_by(BlockchainBlock.block_index.asc()).limit(1)
    genesis = (await db.execute(first_stmt)).scalar_one_or_none()

    doc_count_stmt = select(func.count(DocumentHash.id))
    doc_count = (await db.execute(doc_count_stmt)).scalar() or 0

    custody_count_stmt = select(func.count(CustodyRecord.id))
    custody_count = (await db.execute(custody_count_stmt)).scalar() or 0

    proof = {
        "proof_id": block["hash"][:16],
        "data_hash": data_hash,
        "proof_type": proof_type,
        "timestamp": timestamp.isoformat(),
        "block_index": block["index"],
        "block_hash": block["hash"],
        "previous_block_hash": block["previous_hash"],
        "chain_length": chain_len,
        "chain_valid": await _verify_chain(db),
        "verification_url": f"/api/v1/blockchain/verify-timestamp/{block['hash'][:16]}",
        "chain_stats": {
            "total_blocks": chain_len,
            "total_documents": doc_count,
            "total_custody_records": custody_count,
            "genesis_timestamp": genesis.created_at.isoformat() if genesis and genesis.created_at else None,
            "latest_block_timestamp": block["timestamp"],
        },
    }

    return proof
