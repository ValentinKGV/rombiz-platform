"""
Document Intelligence endpoints — Branch 18.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.document_intelligence import (
    classify_document,
    parse_financial_statement,
    analyze_contract,
    extract_entities,
    compare_documents,
)

router = APIRouter()


class DocumentInput(BaseModel):
    text: str


class DocumentCompareInput(BaseModel):
    text_a: str
    text_b: str


@router.post("/classify")
async def doc_classify(
    body: DocumentInput,
    _user=Depends(get_current_user),
):
    """18.1 — Classify document type."""
    return await classify_document(body.text)


@router.post("/parse-financial")
async def doc_parse_financial(
    body: DocumentInput,
    _user=Depends(get_current_user),
):
    """18.2 — Parse financial statement."""
    return await parse_financial_statement(body.text)


@router.post("/analyze-contract")
async def doc_analyze_contract(
    body: DocumentInput,
    _user=Depends(get_current_user),
):
    """18.3 — Analyze contract clauses."""
    return await analyze_contract(body.text)


@router.post("/extract-entities")
async def doc_extract_entities(
    body: DocumentInput,
    _user=Depends(get_current_user),
):
    """18.4 — Extract named entities."""
    return await extract_entities(body.text)


@router.post("/compare")
async def doc_compare(
    body: DocumentCompareInput,
    _user=Depends(get_current_user),
):
    """18.5 — Compare two document versions."""
    return await compare_documents(body.text_a, body.text_b)
