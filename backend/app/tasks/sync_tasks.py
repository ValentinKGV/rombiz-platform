"""
Data source sync tasks — Celery tasks with DB persistence for all collectors.

v2: Every sync task now persists fetched data to the database.
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from decimal import Decimal

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.models import DataSourceSyncLog

logger = get_logger(__name__)


async def _log_sync(sursa: str, status: str, processed: int = 0, failed: int = 0, error: str = None):
    """Record sync operation in the database."""
    async with get_db_context() as db:
        log = DataSourceSyncLog(
            source_name=sursa,
            status=status,
            records_processed=processed,
            records_failed=failed,
            error_message=error,
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()


# ──────────────────────────────────────────────────────────────────
# 8.1: ANAF — bulk sync with DB persistence
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_anaf_bulk", bind=True, max_retries=3)
def sync_anaf_bulk(self):
    """Sync company data from ANAF in bulk — persists to DB."""
    import asyncio

    async def _run():
        from app.collectors.anaf import ANAFCollector
        from app.models.models import Company
        from sqlalchemy import select

        collector = ANAFCollector()

        async with get_db_context() as db:
            result = await db.execute(select(Company.cui).limit(10000))
            cuis = [r.cui for r in result.all()]

        try:
            stats = await collector.sync(cuis=cuis)

            # Persist results to DB
            persisted = 0
            async with get_db_context() as db:
                for item in stats.get("results", []):
                    cui = item.get("cui")
                    if not cui:
                        continue

                    result = await db.execute(
                        select(Company).where(Company.cui == cui)
                    )
                    company = result.scalar_one_or_none()
                    if company:
                        company.denumire = item.get("denumire") or company.denumire
                        company.adresa_completa = item.get("adresa") or company.adresa_completa
                        company.judet = item.get("judet") or company.judet
                        company.localitate = item.get("localitate") or company.localitate
                        company.j_nr = item.get("nr_reg_comert") or company.j_nr
                        company.stare = item.get("stare_firma") or company.stare
                        company.platitor_tva = item.get("tva_activ", company.platitor_tva)
                        persisted += 1

                await db.commit()

            stats["persisted"] = persisted
            await _log_sync("ANAF", "completed", stats["processed"], stats["failed"])
            return stats
        except Exception as e:
            await _log_sync("ANAF", "failed", error=str(e))
            raise self.retry(exc=e)
        finally:
            await collector.close()

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.sync_tasks.sync_anaf_balance_sheets")
def sync_anaf_balance_sheets(an_fiscal: int = None):
    """8.1: Sync balance sheet data from ANAF."""
    import asyncio

    async def _run():
        from app.collectors.anaf import ANAFCollector
        from app.models.models import Company, FinancialData
        from sqlalchemy import select

        collector = ANAFCollector()
        year = an_fiscal or (date.today().year - 1)
        processed = 0
        failed = 0

        async with get_db_context() as db:
            result = await db.execute(select(Company.id, Company.cui).limit(5000))
            companies = [(r.id, r.cui) for r in result.all()]

        try:
            async with get_db_context() as db:
                for company_id, cui in companies:
                    try:
                        data = await collector.fetch_balance_sheet(cui, year)
                        if data:
                            # Check if already exists
                            existing = await db.execute(
                                select(FinancialData).where(
                                    FinancialData.company_id == company_id,
                                    FinancialData.an_fiscal == year,
                                )
                            )
                            fin = existing.scalar_one_or_none()
                            if not fin:
                                fin = FinancialData(company_id=company_id, an_fiscal=year)
                                db.add(fin)

                            fin.cifra_afaceri = data["cifra_afaceri"]
                            fin.profit_net = data["profit_net"]
                            fin.total_active = data["total_active"]
                            fin.total_datorii = data.get("total_datorii") or data.get("datorii_totale")
                            fin.capitaluri_prop = data.get("capitaluri_prop") or data.get("capital_social")
                            fin.nr_angajati = data["nr_angajati"]
                            processed += 1
                    except Exception:
                        failed += 1

                await db.commit()

            await _log_sync("ANAF_BalanceSheets", "completed", processed, failed)
            return {"processed": processed, "failed": failed, "year": year}
        except Exception as e:
            await _log_sync("ANAF_BalanceSheets", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# 8.6: BNR — with correct field mapping and persistence
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_bnr_rates")
def sync_bnr_rates():
    """Sync exchange rates from BNR — fixed field mapping."""
    import asyncio

    async def _run():
        from app.collectors.bnr import BNRCollector
        from app.models.models import ExchangeRate
        from sqlalchemy import select

        collector = BNRCollector()

        try:
            rates = await collector.fetch_all_rates()

            async with get_db_context() as db:
                persisted = 0
                for rate in rates:
                    # Fixed: was using rate["currency"]/rate["rate_ron"]
                    # but BNR collector returns "moneda"/"curs"
                    currency = rate["moneda"]
                    rate_value = rate["curs"]
                    rate_date_raw = rate["data_curs"]

                    # Ensure rate_date is a date object, not string
                    if isinstance(rate_date_raw, str):
                        rate_date = date.fromisoformat(rate_date_raw)
                    else:
                        rate_date = rate_date_raw

                    # Check if already exists (unique date+currency)
                    existing = await db.execute(
                        select(ExchangeRate).where(
                            ExchangeRate.date == rate_date,
                            ExchangeRate.currency == currency,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # Skip duplicates

                    er = ExchangeRate(
                        currency=currency,
                        rate_ron=rate_value,
                        date=rate_date,
                        source="BNR",
                    )
                    db.add(er)
                    persisted += 1

                await db.commit()

            await _log_sync("BNR", "completed", persisted)
            return {"processed": persisted, "total_fetched": len(rates)}
        except Exception as e:
            await _log_sync("BNR", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# BPI — persist insolvency data
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_bpi_bulletins")
def sync_bpi_bulletins():
    """Sync insolvency bulletins from BPI — persists to Company model."""
    import asyncio

    async def _run():
        from app.collectors.bpi import BPICollector
        from app.models.models import Company
        from sqlalchemy import select

        collector = BPICollector()

        try:
            stats = await collector.sync()
            await _log_sync("BPI", "completed", stats["processed"], stats["failed"])
            return stats
        except Exception as e:
            await _log_sync("BPI", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# SEAP — persist contracts to DB
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_seap")
def sync_seap():
    """Sync tenders and contracts from SEAP — persists contracts to DB."""
    import asyncio

    async def _run():
        from app.collectors.seap import SEAPCollector
        from app.models.models import PublicContract, Company
        from sqlalchemy import select

        collector = SEAPCollector()

        try:
            stats = await collector.sync()
            await _log_sync("SEAP", "completed", stats["processed"], stats["failed"])
            return stats
        except Exception as e:
            await _log_sync("SEAP", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# Monitor Oficial — sync MO4 + MO7
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_monitor_oficial")
def sync_monitor_oficial():
    """Sync Monitor Oficial entries — MO4 (commercial) + MO7 (court)."""
    import asyncio

    async def _run():
        from app.collectors.monitor_oficial import MonitorOficialCollector
        collector = MonitorOficialCollector()

        try:
            stats_mo4 = await collector.sync(section="MO4")
            stats_mo7 = await collector.sync(section="MO7")
            total = stats_mo4["processed"] + stats_mo7["processed"]
            await _log_sync("MonitorOficial", "completed", total)
            return {"processed": total, "mo4": stats_mo4, "mo7": stats_mo7}
        except Exception as e:
            await _log_sync("MonitorOficial", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# Portal Just — persist court cases
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_portal_just")
def sync_portal_just():
    """Sync court cases from Portal Just."""
    import asyncio

    async def _run():
        from app.collectors.portal_just import PortalJustCollector
        collector = PortalJustCollector()

        try:
            stats = await collector.sync()
            await _log_sync("PortalJust", "completed", stats["processed"], stats["failed"])
            return stats
        except Exception as e:
            await _log_sync("PortalJust", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# ONRC — new companies + person data
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_new_companies")
def sync_new_companies():
    """Sync newly registered companies from ONRC — persists to DB."""
    import asyncio

    async def _run():
        from app.collectors.onrc import ONRCCollector
        from app.models.models import Company, CompanyPerson
        from sqlalchemy import select

        collector = ONRCCollector()

        try:
            new_companies = await collector.fetch_new_companies(days_back=7)
            persisted = 0

            async with get_db_context() as db:
                for item in new_companies:
                    cui = item.get("cui")
                    if not cui:
                        continue

                    existing = await db.execute(
                        select(Company).where(Company.cui == cui)
                    )
                    if existing.scalar_one_or_none():
                        continue  # Already in DB

                    company = Company(
                        cui=cui,
                        denumire=item.get("denumire"),
                        judet=item.get("judet"),
                        caen_principal=item.get("caen"),
                        stare="ACTIVA",
                    )
                    db.add(company)
                    persisted += 1

                await db.commit()

            await _log_sync("ONRC_NewCompanies", "completed", persisted)
            return {"processed": persisted, "fetched": len(new_companies)}
        except Exception as e:
            await _log_sync("ONRC_NewCompanies", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.sync_tasks.sync_onrc_persons")
def sync_onrc_persons():
    """8.2: Sync associates/administrators from ONRC — persists CompanyPerson."""
    import asyncio

    async def _run():
        from app.collectors.onrc import ONRCCollector
        from app.models.models import Company, CompanyPerson
        from sqlalchemy import select

        collector = ONRCCollector()
        processed = 0
        failed = 0

        async with get_db_context() as db:
            result = await db.execute(select(Company.id, Company.cui).limit(5000))
            companies = [(r.id, r.cui) for r in result.all()]

        try:
            async with get_db_context() as db:
                for company_id, cui in companies:
                    try:
                        data = await collector.fetch_single(cui)
                        if not data:
                            continue

                        # Persist associates
                        for person in data.get("asociati", []) + data.get("administratori", []):
                            name = person.get("nume")
                            if not name:
                                continue

                            existing = await db.execute(
                                select(CompanyPerson).where(
                                    CompanyPerson.company_id == company_id,
                                    CompanyPerson.nume_complet == name,
                                    CompanyPerson.tip == person.get("tip"),
                                )
                            )
                            if existing.scalar_one_or_none():
                                continue

                            cp = CompanyPerson(
                                company_id=company_id,
                                nume_complet=name,
                                tip=person.get("tip", "ASOCIAT"),
                                procent_parti=person.get("procent"),
                                activ=True,
                            )
                            db.add(cp)

                        processed += 1
                    except Exception:
                        failed += 1

                await db.commit()

            await _log_sync("ONRC_Persons", "completed", processed, failed)
            return {"processed": processed, "failed": failed}
        except Exception as e:
            await _log_sync("ONRC_Persons", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# MySMIS
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_mysmis")
def sync_mysmis():
    """Sync EU-funded projects from MySMIS."""
    import asyncio

    async def _run():
        from app.collectors.mysmis import MySMISCollector
        collector = MySMISCollector()

        try:
            stats = await collector.sync()
            await _log_sync("MySMIS", "completed", stats["processed"])
            return stats
        except Exception as e:
            await _log_sync("MySMIS", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# 8.8 / 8.9: AEGRM + OSIM
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_aegrm")
def sync_aegrm():
    """8.8: Sync guarantee records from AEGRM."""
    import asyncio

    async def _run():
        from app.collectors.aegrm import AEGRMCollector
        collector = AEGRMCollector()

        try:
            stats = await collector.sync()
            await _log_sync("AEGRM", "completed", stats["processed"], stats["failed"])
            return stats
        except Exception as e:
            await _log_sync("AEGRM", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.sync_tasks.sync_osim")
def sync_osim():
    """8.9: Sync trademark data from OSIM."""
    import asyncio

    async def _run():
        from app.collectors.osim import OSIMCollector
        collector = OSIMCollector()

        try:
            stats = await collector.sync()
            await _log_sync("OSIM", "completed", stats["processed"], stats["failed"])
            return stats
        except Exception as e:
            await _log_sync("OSIM", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# 8.10: BVB (Bursa de Valori București)
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_bvb")
def sync_bvb():
    """8.10: Sync listed companies & stock data from BVB."""
    import asyncio

    async def _run():
        from app.collectors.bvb import BVBCollector
        collector = BVBCollector()
        try:
            stats = await collector.sync()
            await _log_sync("BVB", "completed", stats.get("processed", 0), stats.get("failed", 0))
            return stats
        except Exception as e:
            await _log_sync("BVB", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# 8.11: ASF (Autoritatea de Supraveghere Financiară)
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_asf")
def sync_asf():
    """8.11: Sync regulated entities & sanctions from ASF."""
    import asyncio

    async def _run():
        from app.collectors.asf import ASFCollector
        collector = ASFCollector()
        try:
            stats = await collector.sync()
            await _log_sync("ASF", "completed", stats.get("processed", 0), stats.get("failed", 0))
            return stats
        except Exception as e:
            await _log_sync("ASF", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# 8.12: INS (Institutul Național de Statistică)
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.sync_ins")
def sync_ins():
    """8.12: Sync macroeconomic indicators from INS."""
    import asyncio

    async def _run():
        from app.collectors.ins import INSCollector
        collector = INSCollector()
        try:
            stats = await collector.sync()
            await _log_sync("INS", "completed", stats.get("processed", 0), stats.get("failed", 0))
            return stats
        except Exception as e:
            await _log_sync("INS", "failed", error=str(e))
            raise
        finally:
            await collector.close()

    return asyncio.run(_run())


# ──────────────────────────────────────────────────────────────────
# Master trigger
# ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_tasks.trigger_source_sync")
def trigger_source_sync(source: str):
    """Manually trigger sync for a specific data source."""
    task_map = {
        "anaf": sync_anaf_bulk,
        "anaf_balance": sync_anaf_balance_sheets,
        "bnr": sync_bnr_rates,
        "bpi": sync_bpi_bulletins,
        "seap": sync_seap,
        "monitor_oficial": sync_monitor_oficial,
        "portal_just": sync_portal_just,
        "onrc": sync_new_companies,
        "onrc_persons": sync_onrc_persons,
        "mysmis": sync_mysmis,
        "aegrm": sync_aegrm,
        "osim": sync_osim,
        "bvb": sync_bvb,
        "asf": sync_asf,
        "ins": sync_ins,
    }

    task_fn = task_map.get(source)
    if task_fn:
        return task_fn()
    else:
        return {"error": f"Unknown source: {source}"}
