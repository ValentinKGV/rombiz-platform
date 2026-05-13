"""
AI Agent endpoints — Claude-powered business intelligence queries.

v2 Improvements:
  9.1: Extended tools — ESG, fraud, debts, court cases, contracts, associates, exchange rates
  9.2: Streaming with tool support
  9.3: Conversation memory via Redis
  9.5: Proactive insights
  9.6: Token tracking per user
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import (
    Company, FinancialData, RiskScore, ESGScore,
    CompanyPerson, CourtCase, PublicContract, ExchangeRate,
    CompanyDebt, User,
)

router = APIRouter()

SYSTEM_PROMPT = (
    "Ești un asistent AI specialist în analiza firmelor din România. "
    "Răspunzi întotdeauna în limba română. "
    "Folosești date publice disponibile și oferi analize obiective. "
    "Nu faci recomandări de investiții. "
    "Citezi întotdeauna sursele datelor. "
    "Valorile monetare sunt în RON dacă nu se specifică altfel. "
    "Poți folosi uneltele disponibile pentru a căuta date despre firme, "
    "date financiare, scoruri de risc, ESG, dosare, contracte, cursuri BNR."
)

# 9.1: Extended tool definitions
TOOLS = [
    {
        "name": "search_company",
        "description": "Caută informații despre o firmă după CUI sau denumire",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
                "denumire": {"type": "string", "description": "Denumirea firmei"},
            },
        },
    },
    {
        "name": "get_financials",
        "description": "Obține date financiare (bilanț) pentru o firmă pe mai mulți ani",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
                "year": {"type": "integer", "description": "Anul fiscal (opțional)"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_risk_score",
        "description": "Obține scorul de risc al unei firme cu detalii pe subcategorii",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_esg_score",
        "description": "Obține scorul ESG (Environmental, Social, Governance) al unei firme",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_court_cases",
        "description": "Obține dosarele judiciare ale unei firme",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_public_contracts",
        "description": "Obține contractele publice (SEAP) ale unei firme",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
                "limit": {"type": "integer", "description": "Nr. maxim de rezultate (default 10)"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_associates",
        "description": "Obține asociații și administratorii unei firme",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_debts",
        "description": "Obține informații despre datorii fiscale ale unei firme",
        "input_schema": {
            "type": "object",
            "properties": {
                "cui": {"type": "integer", "description": "CUI-ul firmei"},
            },
            "required": ["cui"],
        },
    },
    {
        "name": "get_exchange_rate",
        "description": "Obține cursul BNR pentru o monedă (EUR, USD, GBP, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "Codul monedei (EUR, USD, etc.)"},
            },
            "required": ["currency"],
        },
    },
    {
        "name": "compare_companies",
        "description": "Compară două sau mai multe firme pe indicatori financiari și de risc",
        "input_schema": {
            "type": "object",
            "properties": {
                "cuis": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Lista de CUI-uri de comparat",
                },
            },
            "required": ["cuis"],
        },
    },
]


# ──────────────────────────────────────────────────────────────────
# 9.3: Conversation Memory (Redis)
# ──────────────────────────────────────────────────────────────────

async def _get_conversation(user_id: str) -> list[dict]:
    """Load conversation history from Redis."""
    try:
        from app.core.redis import redis_client
        raw = await redis_client.get(f"ai_conv:{user_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return []


async def _save_conversation(user_id: str, messages: list[dict]):
    """Save conversation history to Redis (max 20 turns)."""
    try:
        from app.core.redis import redis_client
        # Keep last 20 messages to avoid token explosion
        trimmed = messages[-20:]
        await redis_client.setex(
            f"ai_conv:{user_id}",
            3600,  # 1 hour TTL
            json.dumps(trimmed, default=str, ensure_ascii=False),
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
# 9.6: Token Tracking
# ──────────────────────────────────────────────────────────────────

async def _track_tokens(user_id: str, input_tokens: int, output_tokens: int, db: AsyncSession):
    """Track token usage per user."""
    total = input_tokens + output_tokens
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.credits_left is not None:
            # Each 1000 tokens = 1 credit
            credits_used = max(1, total // 1000)
            user.credits_left = max(0, user.credits_left - credits_used)
            await db.flush()
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
# Main Query Endpoint (with tool loop + memory)
# ──────────────────────────────────────────────────────────────────

@router.post("/query")
async def ai_query(
    question: str,
    cui: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Ask the AI agent a natural language question.
    Supports 10 tools, conversation memory, and multi-step tool use.
    """
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="Anthropic SDK not installed")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI agent not configured")

    # Build context
    system = SYSTEM_PROMPT
    if cui:
        result = await db.execute(select(Company).where(Company.cui == cui))
        company = result.scalar_one_or_none()
        if company:
            system += (
                f"\n\nContext: Compania {company.denumire} (CUI {company.cui}), "
                f"Județ: {company.judet}, CAEN: {company.caen_principal}, Stare: {company.stare}"
            )

    # 9.3: Load conversation history
    history = await _get_conversation(str(user.sub))
    history.append({"role": "user", "content": question})

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    total_input = 0
    total_output = 0

    # Multi-step tool loop (max 5 iterations)
    messages = history.copy()
    for _ in range(5):
        response = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        if response.stop_reason == "end_turn":
            # Final text response
            result_text = ""
            for block in response.content:
                if block.type == "text":
                    result_text += block.text
            break

        if response.stop_reason == "tool_use":
            # Process all tool calls
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_data = await _handle_tool_call(block.name, block.input, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_data, default=str, ensure_ascii=False),
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            result_text = ""
            for block in response.content:
                if block.type == "text":
                    result_text += block.text
            break
    else:
        result_text = "Am atins limita de apeluri. Te rog reformulează întrebarea."

    # 9.3: Save conversation
    history.append({"role": "assistant", "content": result_text})
    await _save_conversation(str(user.sub), history)

    # 9.6: Track tokens
    await _track_tokens(str(user.sub), total_input, total_output, db)
    await db.commit()

    return {
        "answer": result_text,
        "model": settings.AI_MODEL,
        "tokens_used": total_input + total_output,
        "input_tokens": total_input,
        "output_tokens": total_output,
    }


# ──────────────────────────────────────────────────────────────────
# 9.2: Streaming with tool support
# ──────────────────────────────────────────────────────────────────

@router.post("/stream")
async def ai_query_stream(
    question: str,
    cui: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Streaming AI query via Server-Sent Events, with tool support."""
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="Anthropic SDK not installed")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI agent not configured")

    system = SYSTEM_PROMPT
    if cui:
        result = await db.execute(select(Company).where(Company.cui == cui))
        company = result.scalar_one_or_none()
        if company:
            system += f"\n\nContext: {company.denumire} (CUI {company.cui})"

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate():
        messages = [{"role": "user", "content": question}]

        # First pass — stream with tools
        with client.messages.stream(
            model=settings.AI_MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            collected_text = ""
            for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta" and hasattr(event, "delta"):
                        if hasattr(event.delta, "text"):
                            collected_text += event.delta.text
                            yield f"data: {json.dumps({'text': event.delta.text}, ensure_ascii=False)}\n\n"

            # Check if tool use happened
            final = stream.get_final_message()
            tool_calls = [b for b in final.content if b.type == "tool_use"]

            if tool_calls:
                yield f"data: {json.dumps({'status': 'processing_tools'})}\n\n"

                messages.append({"role": "assistant", "content": final.content})
                tool_results = []
                for block in tool_calls:
                    tool_data = await _handle_tool_call(block.name, block.input, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_data, default=str, ensure_ascii=False),
                    })
                messages.append({"role": "user", "content": tool_results})

                # Second pass with tool results
                with client.messages.stream(
                    model=settings.AI_MODEL,
                    max_tokens=4096,
                    system=system,
                    messages=messages,
                ) as stream2:
                    for event in stream2:
                        if hasattr(event, "type") and event.type == "content_block_delta":
                            if hasattr(event, "delta") and hasattr(event.delta, "text"):
                                yield f"data: {json.dumps({'text': event.delta.text}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ──────────────────────────────────────────────────────────────────
# Conversation Management
# ──────────────────────────────────────────────────────────────────

@router.delete("/conversation")
async def clear_conversation(user: TokenPayload = Depends(get_current_user)):
    """9.3: Clear conversation history."""
    try:
        from app.core.redis import redis_client
        await redis_client.delete(f"ai_conv:{user.sub}")
    except Exception:
        pass
    return {"status": "cleared"}


@router.get("/conversation")
async def get_conversation_history(user: TokenPayload = Depends(get_current_user)):
    """9.3: Get conversation history."""
    history = await _get_conversation(str(user.sub))
    return {"messages": history, "count": len(history)}


# ──────────────────────────────────────────────────────────────────
# 9.5: Proactive Insights
# ──────────────────────────────────────────────────────────────────

@router.get("/insights/{cui}")
async def proactive_insights(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    9.5: Generate proactive insights for a company.
    Returns up to 5 auto-detected observations.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    insights = []

    # Financial trend
    fin_result = await db.execute(
        select(FinancialData)
        .where(FinancialData.company_id == company.id)
        .order_by(FinancialData.an_fiscal.desc())
        .limit(3)
    )
    financials = fin_result.scalars().all()
    if len(financials) >= 2:
        latest = financials[0]
        prev = financials[1]
        if latest.cifra_afaceri and prev.cifra_afaceri and prev.cifra_afaceri > 0:
            growth = float((latest.cifra_afaceri - prev.cifra_afaceri) / prev.cifra_afaceri * 100)
            if growth > 50:
                insights.append({
                    "type": "positive",
                    "title": "Creștere accelerată",
                    "text": f"Cifra de afaceri a crescut cu {growth:.0f}% în {latest.an_fiscal}.",
                })
            elif growth < -30:
                insights.append({
                    "type": "warning",
                    "title": "Scădere semnificativă",
                    "text": f"Cifra de afaceri a scăzut cu {abs(growth):.0f}% în {latest.an_fiscal}.",
                })

        if latest.profit_net and latest.profit_net < 0:
            insights.append({
                "type": "warning",
                "title": "Pierdere netă",
                "text": f"Compania a raportat pierdere de {abs(float(latest.profit_net)):,.0f} RON în {latest.an_fiscal}.",
            })

    # Risk score
    risk_result = await db.execute(
        select(RiskScore).where(RiskScore.company_id == company.id)
        .order_by(RiskScore.calculat_la.desc()).limit(1)
    )
    risk = risk_result.scalar_one_or_none()
    if risk and risk.rating in ("D", "E"):
        insights.append({
            "type": "danger",
            "title": "Risc ridicat",
            "text": f"Scor de risc: {float(risk.score):.0f}/100 (Rating {risk.rating}).",
        })

    # Court cases
    cases_result = await db.execute(
        select(func.count(CourtCase.id))
        .where(CourtCase.company_id == company.id)
    )
    case_count = cases_result.scalar() or 0
    if case_count > 5:
        insights.append({
            "type": "info",
            "title": "Activitate judiciară",
            "text": f"Compania are {case_count} dosare judiciare înregistrate.",
        })

    # Public contracts
    contracts_result = await db.execute(
        select(func.count(PublicContract.id), func.sum(PublicContract.valoare_ron))
        .where(PublicContract.company_id == company.id)
    )
    row = contracts_result.one()
    if row[0] and row[0] > 0:
        insights.append({
            "type": "info",
            "title": "Contracte publice",
            "text": f"{row[0]} contracte publice, valoare totală {float(row[1] or 0):,.0f} RON.",
        })

    return {"cui": cui, "insights": insights[:5]}


# ──────────────────────────────────────────────────────────────────
# Tool Handler — 9.1 extended
# ──────────────────────────────────────────────────────────────────

async def _handle_tool_call(tool_name: str, tool_input: dict, db: AsyncSession) -> dict:
    """Handle AI agent tool calls — 10 tools supported."""

    if tool_name == "search_company":
        query = select(Company)
        if tool_input.get("cui"):
            query = query.where(Company.cui == tool_input["cui"])
        elif tool_input.get("denumire"):
            query = query.where(Company.denumire.ilike(f"%{tool_input['denumire']}%"))
        result = await db.execute(query.limit(5))
        companies = result.scalars().all()
        return [
            {"cui": c.cui, "denumire": c.denumire, "judet": c.judet,
             "stare": c.stare, "caen": c.caen_principal, "tva": c.platitor_tva}
            for c in companies
        ]

    elif tool_name == "get_financials":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        query = select(FinancialData).where(FinancialData.company_id == company.id)
        if tool_input.get("year"):
            query = query.where(FinancialData.an_fiscal == tool_input["year"])
        result = await db.execute(query.order_by(FinancialData.an_fiscal.desc()).limit(5))
        return [
            {"an": f.an_fiscal, "cifra_afaceri": float(f.cifra_afaceri or 0),
             "profit_net": float(f.profit_net or 0), "angajati": f.nr_angajati,
             "total_active": float(f.total_active or 0), "datorii": float(f.total_datorii or 0)}
            for f in result.scalars().all()
        ]

    elif tool_name == "get_risk_score":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        result = await db.execute(
            select(RiskScore).where(RiskScore.company_id == company.id)
            .order_by(RiskScore.calculat_la.desc()).limit(1)
        )
        risk = result.scalar_one_or_none()
        if not risk:
            return {"error": "Scor de risc indisponibil"}
        return {
            "score": float(risk.score), "rating": risk.rating,
            "financiar": float(risk.scor_financiar or 0),
            "legal": float(risk.scor_legal or 0),
            "fiscal": float(risk.scor_fiscal or 0),
            "comportamental": float(risk.scor_comportamental or 0),
        }

    elif tool_name == "get_esg_score":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        result = await db.execute(
            select(ESGScore).where(ESGScore.company_id == company.id)
            .order_by(ESGScore.calculat_la.desc()).limit(1)
        )
        esg = result.scalar_one_or_none()
        if not esg:
            return {"error": "Scor ESG indisponibil"}
        return {
            "score_total": float(esg.score_total), "e": float(esg.score_e or 0),
            "s": float(esg.score_s or 0), "g": float(esg.score_g or 0),
            "sfdr": esg.sfdr_categoria,
        }

    elif tool_name == "get_court_cases":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        result = await db.execute(
            select(CourtCase).where(CourtCase.company_id == company.id)
            .order_by(CourtCase.ultima_actualizare.desc()).limit(10)
        )
        return [
            {"numar_dosar": c.nr_dosar, "instanta": c.instanta,
             "materie": c.materie, "stadiu": c.stadiu}
            for c in result.scalars().all()
        ]

    elif tool_name == "get_public_contracts":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        limit = tool_input.get("limit", 10)
        result = await db.execute(
            select(PublicContract).where(PublicContract.company_id == company.id)
            .order_by(PublicContract.data_atribuire.desc()).limit(limit)
        )
        return [
            {"titlu": c.titlu_contract, "autoritate": c.autoritate_contractanta,
             "valoare_ron": float(c.valoare_ron or 0),
             "data": str(c.data_atribuire) if c.data_atribuire else None}
            for c in result.scalars().all()
        ]

    elif tool_name == "get_associates":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        result = await db.execute(
            select(CompanyPerson).where(CompanyPerson.company_id == company.id)
        )
        return [
            {"nume": p.nume_complet, "tip": p.tip, "functie": p.tip,
             "procent": float(p.procent_parti or 0), "activ": p.activ}
            for p in result.scalars().all()
        ]

    elif tool_name == "get_debts":
        result = await db.execute(select(Company).where(Company.cui == tool_input["cui"]))
        company = result.scalar_one_or_none()
        if not company:
            return {"error": "Firma nu a fost găsită"}
        result = await db.execute(
            select(CompanyDebt).where(CompanyDebt.company_id == company.id)
            .order_by(CompanyDebt.data_raportare.desc()).limit(10)
        )
        debts = result.scalars().all()
        if not debts:
            return {"info": "Nu sunt datorii restante raportate", "has_debts": company.has_debts}
        return [
            {
                "tip": d.tip_datorie,
                "suma_restanta": float(d.suma_restanta or 0),
                "data_raportare": str(d.data_raportare) if d.data_raportare else None,
                "sursa": d.sursa,
            }
            for d in debts
        ]

    elif tool_name == "get_exchange_rate":
        currency = tool_input["currency"].upper()
        result = await db.execute(
            select(ExchangeRate).where(ExchangeRate.currency == currency)
            .order_by(ExchangeRate.date.desc()).limit(1)
        )
        rate = result.scalar_one_or_none()
        if not rate:
            return {"error": f"Curs {currency} indisponibil"}
        return {
            "currency": rate.currency,
            "rate_ron": float(rate.rate_ron),
            "date": str(rate.date),
            "source": rate.source,
        }

    elif tool_name == "compare_companies":
        cuis = tool_input.get("cuis", [])
        result = await db.execute(select(Company).where(Company.cui.in_(cuis)))
        companies = result.scalars().all()
        comparison = []
        for c in companies:
            fin_r = await db.execute(
                select(FinancialData).where(FinancialData.company_id == c.id)
                .order_by(FinancialData.an_fiscal.desc()).limit(1)
            )
            fin = fin_r.scalar_one_or_none()
            risk_r = await db.execute(
                select(RiskScore).where(RiskScore.company_id == c.id)
                .order_by(RiskScore.calculat_la.desc()).limit(1)
            )
            risk = risk_r.scalar_one_or_none()
            comparison.append({
                "cui": c.cui, "denumire": c.denumire,
                "cifra_afaceri": float(fin.cifra_afaceri) if fin and fin.cifra_afaceri else None,
                "profit": float(fin.profit_net) if fin and fin.profit_net else None,
                "angajati": fin.nr_angajati if fin else None,
                "risk_score": float(risk.score) if risk else None,
                "risk_rating": risk.rating if risk else None,
            })
        return comparison

    return {"error": f"Unealtă necunoscută: {tool_name}"}


# ──────────────────────────────────────────────────────────────────
# Tier 4: AI Compare Companies (narrative analysis)
# ──────────────────────────────────────────────────────────────────

@router.post("/compare")
async def ai_compare_companies(
    cuis: list[int] = Query(..., description="Lista de CUI-uri de comparat"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Compare 2-4 companies with AI-powered narrative analysis.
    Collects financial + risk + ESG data, sends to Claude for expert comparison.
    """
    if len(cuis) < 2 or len(cuis) > 4:
        raise HTTPException(status_code=400, detail="Selectează între 2 și 4 companii")

    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="Anthropic SDK not installed")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI agent not configured")

    # Collect data for each company
    comparison_data = await _handle_tool_call("compare_companies", {"cuis": cuis}, db)

    # Enrich with ESG data
    for item in comparison_data:
        if isinstance(item, dict) and item.get("cui"):
            esg_data = await _handle_tool_call("get_esg_score", {"cui": item["cui"]}, db)
            if isinstance(esg_data, dict) and not esg_data.get("error"):
                item["esg"] = esg_data

    prompt = (
        f"Analizează comparativ următoarele {len(cuis)} companii românești și oferă o "
        f"analiză narativă detaliată. Structurează analiza pe: "
        f"1) Rezumat executiv, 2) Comparație financiară, 3) Profil de risc, "
        f"4) ESG (dacă e disponibil), 5) Puncte forte și slabe pentru fiecare, "
        f"6) Concluzie cu recomandare.\n\n"
        f"Date:\n{json.dumps(comparison_data, default=str, ensure_ascii=False, indent=2)}"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text += block.text

        await _track_tokens(str(user.sub), response.usage.input_tokens, response.usage.output_tokens, db)
        await db.commit()

        return {
            "analysis": result_text,
            "companies": comparison_data,
            "model": settings.AI_MODEL,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        }
    except Exception as e:
        error_msg = str(e)
        if "credit" in error_msg.lower() or "balance" in error_msg.lower():
            raise HTTPException(status_code=503, detail="AI temporar indisponibil — credit insuficient")
        raise HTTPException(status_code=500, detail=f"Eroare AI: {error_msg[:200]}")


# ──────────────────────────────────────────────────────────────────
# Tier 4: AI Report Generation
# ──────────────────────────────────────────────────────────────────

@router.post("/report/{cui}")
async def ai_generate_report(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Generate a comprehensive AI-powered narrative report for a company.
    Collects all available data and generates an expert analysis.
    """
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="Anthropic SDK not installed")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI agent not configured")

    # Collect all company data
    company_data = await _handle_tool_call("search_company", {"cui": cui}, db)
    if isinstance(company_data, list) and len(company_data) == 0:
        raise HTTPException(status_code=404, detail="Companie negăsită")

    financials = await _handle_tool_call("get_financials", {"cui": cui}, db)
    risk_data = await _handle_tool_call("get_risk_score", {"cui": cui}, db)
    esg_data = await _handle_tool_call("get_esg_score", {"cui": cui}, db)
    court_cases = await _handle_tool_call("get_court_cases", {"cui": cui}, db)
    contracts = await _handle_tool_call("get_public_contracts", {"cui": cui, "limit": 5}, db)
    associates = await _handle_tool_call("get_associates", {"cui": cui}, db)
    debts = await _handle_tool_call("get_debts", {"cui": cui}, db)

    all_data = {
        "companie": company_data,
        "financiar": financials,
        "risc": risk_data,
        "esg": esg_data,
        "dosare": court_cases,
        "contracte_publice": contracts,
        "asociati": associates,
        "datorii": debts,
    }

    prompt = (
        "Generează un raport complet de due diligence pentru compania de mai jos. "
        "Structurează raportul pe secțiuni:\n"
        "1. **Rezumat Executiv** — concluzii cheie în 3-4 propoziții\n"
        "2. **Informații Generale** — identificare, activitate, management\n"
        "3. **Analiză Financiară** — evoluție CA, profit, lichiditate, îndatorare\n"
        "4. **Profil de Risc** — scorul global și pe componente, trend\n"
        "5. **ESG** — dacă există date, scoruri E/S/G\n"
        "6. **Activitate Juridică** — dosare, litigii active\n"
        "7. **Contracte Publice** — participare SEAP\n"
        "8. **Structură Acționariat** — asociați, administratori\n"
        "9. **Datorii** — situație fiscală\n"
        "10. **Concluzii și Recomandări** — evaluare finală\n\n"
        f"Date:\n{json.dumps(all_data, default=str, ensure_ascii=False, indent=2)}"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text += block.text

        await _track_tokens(str(user.sub), response.usage.input_tokens, response.usage.output_tokens, db)
        await db.commit()

        return {
            "report": result_text,
            "cui": cui,
            "model": settings.AI_MODEL,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        }
    except Exception as e:
        error_msg = str(e)
        if "credit" in error_msg.lower() or "balance" in error_msg.lower():
            raise HTTPException(status_code=503, detail="AI temporar indisponibil — credit insuficient")
        raise HTTPException(status_code=500, detail=f"Eroare AI: {error_msg[:200]}")


# ──────────────────────────────────────────────────────────────────
# Tier 4: AI Summary (compact, for profile page)
# ──────────────────────────────────────────────────────────────────

@router.get("/summary/{cui}")
async def ai_company_summary(
    cui: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Generate a short AI summary (~150 words) for a company profile card.
    Uses cache via Redis to avoid repeat calls.
    """
    # Check Redis cache first
    cache_key = f"ai_summary:{cui}"
    try:
        from app.core.redis import redis_client
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="Anthropic SDK not installed")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI agent not configured")

    # Collect essential data
    company_data = await _handle_tool_call("search_company", {"cui": cui}, db)
    financials = await _handle_tool_call("get_financials", {"cui": cui}, db)
    risk_data = await _handle_tool_call("get_risk_score", {"cui": cui}, db)

    prompt = (
        "Generează un sumar scurt (maxim 150 de cuvinte, un singur paragraf) "
        "despre compania de mai jos. Include: sectorul de activitate, "
        "performanța financiară recentă, tendința de creștere/scădere, "
        "nivelul de risc, și un punct notabil. Tonul trebuie să fie profesional "
        "și informativ.\n\n"
        f"Companie: {json.dumps(company_data, default=str, ensure_ascii=False)}\n"
        f"Financiar: {json.dumps(financials, default=str, ensure_ascii=False)}\n"
        f"Risc: {json.dumps(risk_data, default=str, ensure_ascii=False)}"
    )

    try:
        import asyncio
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        def _call_anthropic():
            return client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

        response = await asyncio.to_thread(_call_anthropic)

        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text += block.text

        await _track_tokens(str(user.sub), response.usage.input_tokens, response.usage.output_tokens, db)
        await db.commit()

        result = {
            "summary": result_text,
            "cui": cui,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Cache for 24 hours
        try:
            from app.core.redis import redis_client
            await redis_client.setex(cache_key, 86400, json.dumps(result, ensure_ascii=False))
        except Exception:
            pass

        return result
    except Exception as e:
        error_msg = str(e)
        if "credit" in error_msg.lower() or "balance" in error_msg.lower():
            raise HTTPException(status_code=503, detail="AI temporar indisponibil — credit insuficient")
        raise HTTPException(status_code=500, detail=f"Eroare AI: {error_msg[:200]}")
