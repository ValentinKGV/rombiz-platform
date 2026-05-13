"""
CRM Bridge endpoints — read-only access to ATH|CRM (kloth_crm) database.
Provides aggregated stats, pipeline data, and contract info for the CRM dashboard.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_crm_db

router = APIRouter()


@router.get("/stats")
async def crm_stats(
    db: AsyncSession = Depends(get_crm_db),
):
    """Aggregate CRM KPIs for the dashboard cards."""

    queries = {
        # Total vânzări = sum of offers that converted to contracts
        "totalVanzari": "SELECT COALESCE(SUM(valoare_oferta), 0) FROM sales_pipeline WHERE status = 'contract'",
        # Total clienți activi
        "totalClienti": "SELECT COUNT(*) FROM sales_pipeline_clienti",
        # Total facturat
        "totalFacturat": "SELECT COALESCE(SUM(valoare_totala), 0) FROM facturi_clienti",
        # Total încasat
        "totalIncasat": "SELECT COALESCE(SUM(valoare_totala), 0) FROM facturi_clienti WHERE status = 'incasata'",
        # Valoare oferte (pipeline activ, excl. contracte + pierduți)
        "valoareOferte": "SELECT COALESCE(SUM(valoare_oferta), 0) FROM sales_pipeline WHERE status NOT IN ('contract', 'client_pierdut')",
        # Potențiali clienți (pipeline activ)
        "potentialiClienti": "SELECT COUNT(*) FROM sales_pipeline WHERE status NOT IN ('contract', 'client_pierdut')",
        # Oferte pierdute
        "totalOfertepierdute": "SELECT COALESCE(SUM(valoare_oferta), 0) FROM sales_pipeline_clienti_pierduti",
        # Clienți pierduți
        "totalClientiPierduti": "SELECT COUNT(*) FROM sales_pipeline_clienti_pierduti",
        # Rest de încasat = facturat - încasat
        "restDeIncasat": """
            SELECT COALESCE(SUM(valoare_totala), 0)
            FROM facturi_clienti
            WHERE status NOT IN ('incasata', 'anulata')
        """,
        # Durata medie încasare (days between emit and scadenta for paid invoices)
        "durataMedieIncasare": """
            SELECT COALESCE(AVG(data_scadenta - data_emitere), 0)
            FROM facturi_clienti
            WHERE status = 'incasata' AND data_scadenta IS NOT NULL AND data_emitere IS NOT NULL
        """,
        # Durata medie vânzare (pipeline KPI)
        "durataMedieVanzare": """
            SELECT COALESCE(AVG(kpi_durata_vanzare), 0)
            FROM sales_pipeline
            WHERE kpi_durata_vanzare > 0
        """,
        # Valoare contracte
        "valoareContracte": "SELECT COALESCE(SUM(valoare_contract), 0) FROM sales_pipeline_clienti",
        # Nr contracte
        "nrContracte": "SELECT COUNT(*) FROM sales_pipeline_clienti WHERE valoare_contract > 0",
    }

    result = {}
    for key, sql in queries.items():
        row = await db.execute(text(sql))
        val = row.scalar()
        result[key] = float(val) if val is not None else 0.0

    # Rata conversie = clienți / (clienți + pierduți) * 100
    total_clienti = result["totalClienti"]
    total_pierduti = result["totalClientiPierduti"]
    denominator = total_clienti + total_pierduti
    result["rataConversie"] = round(
        (total_clienti / denominator * 100) if denominator > 0 else 0, 1
    )

    return result


@router.get("/contracte")
async def crm_contracte(
    period: str = Query("luna", regex="^(zi|saptamana|luna|an)$"),
    db: AsyncSession = Depends(get_crm_db),
):
    """Recent contracts filtered by period, for the Contracte widget."""
    today = date.today()
    if period == "zi":
        start = today
    elif period == "saptamana":
        start = today - timedelta(days=7)
    elif period == "luna":
        start = today - timedelta(days=30)
    else:  # an
        start = today - timedelta(days=365)

    sql = text("""
        SELECT
            id, potential_client, valoare_oferta, valoare_contract,
            data_inchidere_vanzare, serviciu_denumire, numar_contract
        FROM sales_pipeline_clienti
        WHERE data_inchidere_vanzare >= :start_date
        ORDER BY data_inchidere_vanzare DESC
        LIMIT 50
    """)
    rows = await db.execute(sql, {"start_date": start})
    items = []
    for r in rows.fetchall():
        items.append({
            "id": r[0],
            "client": r[1],
            "valoareOferta": float(r[2] or 0),
            "valoareContract": float(r[3] or 0),
            "dataInchidere": str(r[4]) if r[4] else None,
            "serviciu": r[5],
            "numarContract": r[6],
        })

    # Also get totals for the period
    totals_sql = text("""
        SELECT COALESCE(SUM(valoare_contract), 0), COUNT(*)
        FROM sales_pipeline_clienti
        WHERE data_inchidere_vanzare >= :start_date AND valoare_contract > 0
    """)
    totals = await db.execute(totals_sql, {"start_date": start})
    row = totals.fetchone()

    return {
        "valoareContracte": float(row[0]) if row else 0.0,
        "nrContracte": int(row[1]) if row else 0,
        "items": items,
    }


@router.get("/pipeline")
async def crm_pipeline(
    db: AsyncSession = Depends(get_crm_db),
):
    """Pipeline breakdown by status for charts."""
    sql = text("""
        SELECT status, COUNT(*) as cnt, COALESCE(SUM(valoare_oferta), 0) as total
        FROM sales_pipeline
        GROUP BY status
        ORDER BY cnt DESC
    """)
    rows = await db.execute(sql)
    items = []
    for r in rows.fetchall():
        items.append({
            "status": r[0],
            "count": r[1],
            "valoare": float(r[2]),
        })
    return {"pipeline": items}


@router.get("/facturi")
async def crm_facturi(
    db: AsyncSession = Depends(get_crm_db),
):
    """Recent invoices."""
    sql = text("""
        SELECT id, numar_factura, denumire_client, valoare_totala,
               status, data_emitere, data_scadenta
        FROM facturi_clienti
        ORDER BY data_emitere DESC
        LIMIT 50
    """)
    rows = await db.execute(sql)
    items = []
    for r in rows.fetchall():
        items.append({
            "id": r[0],
            "numarFactura": r[1],
            "client": r[2],
            "valoareTotala": float(r[3] or 0),
            "status": r[4],
            "dataEmitere": str(r[5]) if r[5] else None,
            "dataScadenta": str(r[6]) if r[6] else None,
        })
    return {"facturi": items}


@router.get("/top-clienti-pierduti")
async def crm_top_clienti_pierduti(
    db: AsyncSession = Depends(get_crm_db),
):
    """Top lost clients by offer value."""
    sql = text("""
        SELECT potential_client, valoare_oferta, motiv_pierdere, data_pierdere
        FROM sales_pipeline_clienti_pierduti
        WHERE valoare_oferta > 0
        ORDER BY valoare_oferta DESC
        LIMIT 20
    """)
    rows = await db.execute(sql)
    items = []
    for r in rows.fetchall():
        items.append({
            "client": r[0],
            "valoareOferta": float(r[1] or 0),
            "motivPierdere": r[2],
            "dataPierdere": str(r[3]) if r[3] else None,
        })
    return {"clientiPierduti": items}
