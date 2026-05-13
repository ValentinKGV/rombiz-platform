"""
BVB (Bursa de Valori București) endpoints.
Returnează companiile listate la bursă cu datele de piață din data_sources.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Company

router = APIRouter()


@router.get("/companies")
async def get_bvb_companies(
    segment: Optional[str] = Query(default=None, description="Premium | Standard | AeRO"),
    sort_by: str = Query(default="last_price", description="last_price | change_pct | denumire"),
    sort_dir: str = Query(default="desc", description="asc | desc"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, le=200),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Lista tuturor companiilor listate la BVB cu datele de piață (deduplicate per ISIN)."""
    import json
    from sqlalchemy import text

    # Map sort_by to SQL expression
    sort_expr = {
        "last_price": "(data_sources::jsonb->'bvb'->>'last_price')::float",
        "change_pct": "(data_sources::jsonb->'bvb'->>'change_pct')::float",
        "denumire": "denumire",
    }.get(sort_by, "(data_sources::jsonb->'bvb'->>'last_price')::float")

    direction = "DESC" if sort_dir == "desc" else "ASC"
    nulls = "NULLS LAST" if sort_dir == "desc" else "NULLS FIRST"

    seg_filter = ""
    params: dict = {}
    if segment:
        seg_filter = "AND data_sources::jsonb->'bvb'->>'segment' = :segment"
        params["segment"] = segment

    # Deduplicate by ISIN — keep the row with highest price (prefer real listed company)
    base_sql = f"""
        SELECT DISTINCT ON (data_sources::jsonb->'bvb'->>'isin')
            id, cui, denumire, judet, data_sources
        FROM companies
        WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
          {seg_filter}
        ORDER BY data_sources::jsonb->'bvb'->>'isin',
                 (data_sources::jsonb->'bvb'->>'last_price')::float DESC NULLS LAST
    """

    count_sql = f"SELECT COUNT(*) FROM ({base_sql}) sub"
    total_result = await db.execute(text(count_sql).bindparams(**params))
    total = total_result.scalar_one()

    paged_sql = f"""
        SELECT * FROM (
            SELECT DISTINCT ON (data_sources::jsonb->'bvb'->>'isin')
                id, cui, denumire, judet, caen_principal, data_sources
            FROM companies
            WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
              {seg_filter}
            ORDER BY data_sources::jsonb->'bvb'->>'isin',
                     (data_sources::jsonb->'bvb'->>'last_price')::float DESC NULLS LAST
        ) sub
        ORDER BY {sort_expr} {direction} {nulls}
        LIMIT :limit OFFSET :offset
    """
    params_paged = {**params, "limit": per_page, "offset": (page - 1) * per_page}
    rows = (await db.execute(text(paged_sql).bindparams(**params_paged))).all()

    items = []
    for row in rows:
        ds = row.data_sources
        if isinstance(ds, str):
            try:
                ds = json.loads(ds)
            except Exception:
                ds = {}
        bvb = ds.get("bvb", {}) if ds else {}
        items.append(
            {
                "id": row.id,
                "cui": row.cui,
                "denumire": row.denumire,
                "judet": row.judet,
                "cod_caen": row.caen_principal,
                "ticker": bvb.get("ticker"),
                "isin": bvb.get("isin"),
                "last_price": bvb.get("last_price"),
                "change_pct": bvb.get("change_pct"),
                "volume": bvb.get("volume"),
                "market_cap": bvb.get("market_cap"),
                "segment": bvb.get("segment"),
                "market": bvb.get("market", "BVB"),
                "updated_at": bvb.get("updated_at"),
            }
        )

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": items,
    }


@router.get("/stats")
async def get_bvb_stats(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Statistici agregate BVB: total listate, pe segment, gainers/losers, etc."""
    from sqlalchemy import text

    # Deduplicate by ISIN (same BVB instrument may appear on multiple DB company rows)
    result = await db.execute(
        text("""
        WITH dedup AS (
          SELECT DISTINCT ON (data_sources::jsonb->'bvb'->>'isin')
            id, cui, denumire,
            data_sources::jsonb->'bvb'->>'isin'       AS isin,
            data_sources::jsonb->'bvb'->>'ticker'     AS ticker,
            data_sources::jsonb->'bvb'->>'segment'    AS segment,
            (data_sources::jsonb->'bvb'->>'last_price')::float  AS last_price,
            (data_sources::jsonb->'bvb'->>'change_pct')::float  AS change_pct
          FROM companies
          WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
          ORDER BY data_sources::jsonb->'bvb'->>'isin',
                   (data_sources::jsonb->'bvb'->>'last_price')::float DESC NULLS LAST
        )
        SELECT
          COUNT(*)                                              AS total,
          COUNT(*) FILTER (WHERE segment = 'Premium')          AS premium,
          COUNT(*) FILTER (WHERE segment = 'Standard')         AS standard,
          COUNT(*) FILTER (WHERE segment = 'AeRO')             AS aero,
          COUNT(*) FILTER (WHERE change_pct > 0)               AS gainers,
          COUNT(*) FILTER (WHERE change_pct < 0)               AS losers,
          COUNT(*) FILTER (WHERE change_pct = 0)               AS unchanged,
          AVG(change_pct)                                       AS avg_change_pct,
          MAX(last_price)                                       AS max_price,
          MIN(last_price)                                       AS min_price
        FROM dedup
        """)
    )
    row = result.mappings().one()

    # Top gainers (deduplicated)
    gainers_res = await db.execute(
        text("""
        SELECT DISTINCT ON (data_sources::jsonb->'bvb'->>'isin')
          denumire, cui,
          data_sources::jsonb->'bvb'->>'ticker'   AS ticker,
          (data_sources::jsonb->'bvb'->>'last_price')::float  AS last_price,
          (data_sources::jsonb->'bvb'->>'change_pct')::float  AS change_pct,
          data_sources::jsonb->'bvb'->>'segment'  AS segment
        FROM companies
        WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
          AND (data_sources::jsonb->'bvb'->>'change_pct')::float > 0
        ORDER BY data_sources::jsonb->'bvb'->>'isin',
                 (data_sources::jsonb->'bvb'->>'change_pct')::float DESC
        LIMIT 10
        """)
    )
    # Re-sort by change_pct descending and take top 5
    gainers = sorted(
        [dict(r) for r in gainers_res.mappings()],
        key=lambda x: x["change_pct"] or 0,
        reverse=True,
    )[:5]

    # Top losers (deduplicated)
    losers_res = await db.execute(
        text("""
        SELECT DISTINCT ON (data_sources::jsonb->'bvb'->>'isin')
          denumire, cui,
          data_sources::jsonb->'bvb'->>'ticker'   AS ticker,
          (data_sources::jsonb->'bvb'->>'last_price')::float  AS last_price,
          (data_sources::jsonb->'bvb'->>'change_pct')::float  AS change_pct,
          data_sources::jsonb->'bvb'->>'segment'  AS segment
        FROM companies
        WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
          AND (data_sources::jsonb->'bvb'->>'change_pct')::float < 0
        ORDER BY data_sources::jsonb->'bvb'->>'isin',
                 (data_sources::jsonb->'bvb'->>'change_pct')::float ASC
        LIMIT 10
        """)
    )
    losers = sorted(
        [dict(r) for r in losers_res.mappings()],
        key=lambda x: x["change_pct"] or 0,
    )[:5]

    # By segment distribution (deduplicated)
    seg_res = await db.execute(
        text("""
        WITH dedup AS (
          SELECT DISTINCT ON (data_sources::jsonb->'bvb'->>'isin')
            COALESCE(data_sources::jsonb->'bvb'->>'segment', 'Necunoscut') AS segment
          FROM companies
          WHERE data_sources::jsonb->'bvb'->>'listed' = 'true'
          ORDER BY data_sources::jsonb->'bvb'->>'isin'
        )
        SELECT segment, COUNT(*) AS count
        FROM dedup
        GROUP BY segment
        ORDER BY count DESC
        """)
    )
    by_segment = [dict(r) for r in seg_res.mappings()]

    return {
        "total": row["total"],
        "premium": row["premium"],
        "standard": row["standard"],
        "aero": row["aero"],
        "gainers": row["gainers"],
        "losers": row["losers"],
        "unchanged": row["unchanged"],
        "avg_change_pct": round(float(row["avg_change_pct"] or 0), 2),
        "max_price": row["max_price"],
        "min_price": row["min_price"],
        "top_gainers": gainers,
        "top_losers": losers,
        "by_segment": by_segment,
    }
