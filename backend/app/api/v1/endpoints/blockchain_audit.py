"""
Blockchain Audit endpoints — audit trail, document hashing,
smart contract verification, chain of custody, and timestamps.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.blockchain_audit import (
    audit_trail,
    hash_document,
    verify_document,
    smart_contract_check,
    chain_of_custody,
    timestamp_proof,
)

router = APIRouter()


# ── Pydantic body models ──────────────────────────────────────
class DocumentHashBody(BaseModel):
    document_content: str
    document_name: str = "Document"
    company_id: int | None = None


class DocumentVerifyBody(BaseModel):
    document_content: str


class CustodyBody(BaseModel):
    action: str | None = None
    details: str | None = None


class TimestampBody(BaseModel):
    data: str
    proof_type: str = "generic"
    company_id: int | None = None


# ── Endpoints ─────────────────────────────────────────────────
@router.get("/audit-trail/{company_id}")
async def get_audit_trail(
    company_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await audit_trail(db, company_id, limit)


@router.post("/hash-document")
async def hash_doc(
    body: DocumentHashBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await hash_document(db, body.document_content, body.document_name, body.company_id, user.id)


@router.post("/verify-document")
async def verify_doc(
    body: DocumentVerifyBody,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await verify_document(db, body.document_content)


@router.get("/smart-contract/{company_id}")
async def smart_contract(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await smart_contract_check(db, company_id)


@router.get("/custody/{company_id}")
async def get_custody(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await chain_of_custody(db, company_id)


@router.post("/custody/{company_id}")
async def add_custody(
    company_id: int,
    body: CustodyBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await chain_of_custody(db, company_id, body.action, body.details, user.id)


@router.post("/timestamp")
async def create_timestamp(
    body: TimestampBody,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await timestamp_proof(db, body.data, body.proof_type, body.company_id)
