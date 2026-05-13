"""
Database engine & session factory for async SQLAlchemy.
Supports PostgreSQL (production) and SQLite (development).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.DATABASE_ECHO,
}

if _is_sqlite:
    # SQLite doesn't support pool_size/max_overflow/pool_pre_ping
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ── CRM Database (read-only bridge to ATH|CRM) ──────────────────
_crm_engine = None
_CrmSessionLocal = None

# ── CO2 Database (read-only bridge to carbon tracking) ───────────
_co2_engine = None
_Co2SessionLocal = None

if settings.CRM_DATABASE_URL:
    _crm_engine = create_async_engine(
        settings.CRM_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=3,
        pool_pre_ping=True,
    )
    _CrmSessionLocal = async_sessionmaker(
        _crm_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_crm_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields a read-only async session to the CRM database."""
    if _CrmSessionLocal is None:
        raise RuntimeError("CRM_DATABASE_URL is not configured")
    async with _CrmSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


if settings.CO2_DATABASE_URL:
    _co2_engine = create_async_engine(
        settings.CO2_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=3,
        pool_pre_ping=True,
    )
    _Co2SessionLocal = async_sessionmaker(
        _co2_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_co2_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields a read-only async session to the CO2 database."""
    if _Co2SessionLocal is None:
        raise RuntimeError("CO2_DATABASE_URL is not configured")
    async with _Co2SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager variant for use outside FastAPI (Celery tasks, scripts).
    Creates a fresh engine to avoid event-loop conflicts in Celery workers."""
    from sqlalchemy.ext.asyncio import create_async_engine as _create_engine, async_sessionmaker as _sessionmaker
    _eng = _create_engine(settings.DATABASE_URL, **_engine_kwargs)
    _session_factory = _sessionmaker(_eng, class_=AsyncSession, expire_on_commit=False)
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    await _eng.dispose()
