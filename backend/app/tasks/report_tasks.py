"""
Report generation Celery tasks.
"""
from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.report_tasks.generate_company_report_task")
def generate_company_report_task(
    company_id: int,
    user_id: str,
    format: str = "pdf",
    sections: list[str] = None,
):
    """Generate a company report (PDF or Excel)."""

    async def _run():
        from app.services.reports_service import ReportService
        from app.models.models import ReportExport
        from sqlalchemy import select, and_

        async with get_db_context() as db:
            service = ReportService(db)

            try:
                if format == "pdf":
                    content = await service.generate_company_pdf(company_id, sections or ["general"])
                    content_type = "application/pdf"
                    ext = "pdf"
                else:
                    content = await service.generate_company_excel(company_id, sections or ["general"])
                    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ext = "xlsx"

                # Upload to MinIO
                file_url = await service.upload_to_minio(
                    content,
                    f"company_{company_id}.{ext}",
                    content_type=content_type,
                )
                if not file_url:
                    file_url = f"/reports/company_{company_id}.{ext}"

                # Update export record
                result = await db.execute(
                    select(ReportExport).where(
                        and_(
                            ReportExport.company_id == company_id,
                            ReportExport.user_id == user_id,
                            ReportExport.status == "processing",
                        )
                    ).order_by(ReportExport.created_at.desc()).limit(1)
                )
                export = result.scalar_one_or_none()
                if export:
                    export.status = "completed"
                    export.file_url = file_url
                    await db.commit()

                return {
                    "status": "completed",
                    "file_url": file_url,
                    "size_bytes": len(content),
                }

            except Exception as e:
                logger.error("report_generation_failed", error=str(e))
                raise

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.report_tasks.generate_portfolio_report_task")
def generate_portfolio_report_task(
    portfolio_id: int,
    user_id: str,
    format: str = "pdf",
):
    """Generate a portfolio aggregate report (7.4)."""

    async def _run():
        from app.services.reports_service import ReportService
        from app.models.models import ReportExport
        from sqlalchemy import select, and_

        async with get_db_context() as db:
            service = ReportService(db)

            try:
                if format == "pdf":
                    content = await service.generate_portfolio_pdf(portfolio_id, user_id)
                    ext = "pdf"
                else:
                    content = await service.generate_portfolio_excel(portfolio_id, user_id)
                    ext = "xlsx"

                # Upload to MinIO
                content_type = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                file_url = await service.upload_to_minio(
                    content,
                    f"portfolio_{portfolio_id}.{ext}",
                    content_type=content_type,
                )
                if not file_url:
                    file_url = f"/reports/portfolio_{portfolio_id}.{ext}"

                # Update export record
                result = await db.execute(
                    select(ReportExport).where(
                        and_(
                            ReportExport.user_id == user_id,
                            ReportExport.status == "processing",
                        )
                    ).order_by(ReportExport.created_at.desc()).limit(1)
                )
                export = result.scalar_one_or_none()
                if export:
                    export.status = "completed"
                    export.file_url = file_url
                    await db.commit()

                return {
                    "status": "completed",
                    "file_url": file_url,
                    "size_bytes": len(content),
                }

            except Exception as e:
                logger.error("portfolio_report_failed", error=str(e))
                raise

    return asyncio.run(_run())
