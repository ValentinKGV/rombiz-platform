"""
Reports endpoints — PDF/Excel/CSV/JSON/HTML export, portfolio reports, scheduled reports.
"""
from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Company, ReportExport

router = APIRouter()


@router.post("/company/{cui}")
async def generate_company_report(
    cui: int,
    format: str = Query(default="pdf", pattern="^(pdf|xlsx|csv|json|html)$"),
    sections: Optional[list[str]] = Query(
        default=None,
        description="Sections: general, financial, legal, risk, esg, contracts, persons"
    ),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Generate a company report in PDF, Excel, CSV, JSON, or HTML format.
    CSV format requires a single section parameter.
    """
    result = await db.execute(select(Company).where(Company.cui == cui))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    effective_sections = sections or ["general", "financial", "legal", "risk"]

    # 7.3: For small/instant formats (CSV, JSON, HTML), return inline
    if format in ("csv", "json", "html"):
        from app.services.reports_service import ReportService
        svc = ReportService(db)

        if format == "csv":
            section = effective_sections[0] if effective_sections else "financial"
            content = await svc.generate_company_csv(company.id, section)
            return StreamingResponse(
                io.BytesIO(content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=company_{cui}_{section}.csv"},
            )
        elif format == "json":
            content = await svc.generate_company_json(company.id, effective_sections)
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=company_{cui}.json"},
            )
        else:  # html
            content = await svc.generate_company_html(company.id, effective_sections)
            return StreamingResponse(
                io.BytesIO(content),
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=company_{cui}.html"},
            )

    # PDF/XLSX — async via Celery
    from app.tasks.report_tasks import generate_company_report_task
    task = generate_company_report_task.delay(
        company_id=company.id,
        user_id=str(user.sub),
        format=format,
        sections=effective_sections,
    )

    export = ReportExport(
        user_id=user.sub,
        company_id=company.id,
        export_type="company_profile",
        format=format,
        status="processing",
        task_id=str(task.id),
    )
    db.add(export)
    await db.commit()

    return {
        "status": "generating",
        "task_id": str(task.id),
        "export_id": export.id,
    }


@router.post("/portfolio/{portfolio_id}")
async def generate_portfolio_report(
    portfolio_id: int,
    format: str = Query(default="pdf", pattern="^(pdf|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Generate a portfolio-level aggregate report.
    """
    from app.models.models import MonitoredPortfolio

    result = await db.execute(
        select(MonitoredPortfolio).where(
            and_(MonitoredPortfolio.id == portfolio_id, MonitoredPortfolio.user_id == user.sub)
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from app.tasks.report_tasks import generate_portfolio_report_task
    task = generate_portfolio_report_task.delay(
        portfolio_id=portfolio_id,
        user_id=str(user.sub),
        format=format,
    )

    export = ReportExport(
        user_id=user.sub,
        export_type="portfolio",
        format=format,
        status="processing",
        task_id=str(task.id),
    )
    db.add(export)
    await db.commit()

    return {"status": "generating", "task_id": str(task.id), "export_id": export.id}


@router.get("/exports")
async def list_exports(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    List all report exports for the current user.
    """
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ReportExport)
        .where(ReportExport.user_id == user.sub)
        .order_by(ReportExport.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    exports = result.scalars().all()
    return [
        {
            "id": e.id,
            "export_type": e.export_type,
            "format": e.format,
            "status": e.status,
            "file_url": e.file_url,
            "created_at": e.created_at,
        }
        for e in exports
    ]


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    Download a generated report by streaming it from MinIO.
    """
    result = await db.execute(
        select(ReportExport).where(
            and_(ReportExport.id == export_id, ReportExport.user_id == user.sub)
        )
    )
    export = result.scalar_one_or_none()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    if export.status != "completed":
        raise HTTPException(status_code=409, detail=f"Export status: {export.status}")

    if not export.file_url:
        raise HTTPException(status_code=404, detail="File not available")

    # Parse bucket and object_name from the stored presigned URL
    from urllib.parse import urlparse, parse_qs
    from app.core.config import settings

    try:
        from minio import Minio
    except ImportError:
        raise HTTPException(status_code=501, detail="MinIO client not available")

    parsed = urlparse(export.file_url)
    # Presigned URL path format: /<bucket>/<object_name>
    path_parts = parsed.path.lstrip("/").split("/", 1)
    if len(path_parts) < 2:
        raise HTTPException(status_code=404, detail="Invalid file reference")

    bucket_name = path_parts[0]
    object_name = path_parts[1]

    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    try:
        response = client.get_object(bucket_name, object_name)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")

    content_type_map = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json",
        "html": "text/html",
    }
    media_type = content_type_map.get(export.format, "application/octet-stream")
    filename = object_name.rsplit("/", 1)[-1]

    def _iter_file():
        try:
            for chunk in response.stream(8192):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(
        _iter_file(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
