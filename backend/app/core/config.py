"""
RomBiz Intelligence Platform — Configuration
All settings loaded from environment variables with safe defaults.
"""
from __future__ import annotations

import secrets
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration — loaded from .env or environment variables."""

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "RomBiz Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    BASE_URL: str = "https://api.rombiz.ro"
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Database (PostgreSQL or SQLite for dev) ────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./rombiz_dev.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # ── CRM Database (read-only bridge to ATH|CRM) ──────────────────
    CRM_DATABASE_URL: str = ""

    # ── CO2 Database (read-only bridge to carbon tracking DB) ────────
    CO2_DATABASE_URL: str = ""

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour default

    # ── Celery ───────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Elasticsearch ────────────────────────────────────────────────
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "rombiz"

    # ── Neo4j (Fraud Graph) ──────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j_secret"

    # ── MinIO / S3 ───────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_REPORTS: str = "reports"
    MINIO_BUCKET_PDFS: str = "pdfs"
    MINIO_SECURE: bool = False

    # ── JWT Authentication ───────────────────────────────────────────
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── GDPR ─────────────────────────────────────────────────────────
    CNP_PEPPER: str = Field(default_factory=lambda: secrets.token_hex(32))
    AUDIT_LOG_RETENTION_DAYS: int = 90
    IP_ANONYMIZE_AFTER_DAYS: int = 30

    # ── External APIs ────────────────────────────────────────────────
    ANAF_WEBSERVICE_URL: str = "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva"
    ANAF_STATIC_BASE_URL: str = "https://static.anaf.ro/static/10/Anaf/informatii_R/"
    ANAF_BATCH_SIZE: int = 500
    ANAF_RATE_LIMIT_RPS: int = 8

    BNR_DAILY_URL: str = "https://www.bnr.ro/nbrfxrates.xml"
    BNR_HISTORIC_URL: str = "https://www.bnr.ro/files/xml/years/nbrfxrates{year}.xml"

    BPI_RSS_URL: str = "https://www.buletinul.ro/rss/"
    MO_RSS_MO4: str = "https://www.monitoruloficial.ro/rss/mo4.xml"
    MO_RSS_MO7: str = "https://www.monitoruloficial.ro/rss/mo7.xml"

    SEAP_API_URL: str = "https://sicap-prod.e-licitatie.ro/api/"

    ONRC_RECOM_URL: str = "https://recom.onrc.ro/"
    ONRC_CACHE_TTL_DAYS: int = 30
    ONRC_RATE_LIMIT_RPS: float = 1.0

    # BERC portal credentials (optional — enables RPA enrichment for ONRC)
    BERC_EMAIL: str = ""
    BERC_PASSWORD: str = ""

    # ── AI Agent ─────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-3-5-haiku-20241022"

    # ── Email / SMS ──────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@rombiz.ro"
    SMS_PROVIDER_API_KEY: str = ""

    # ── Twilio (SMS) ─────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT_RPM: int = 60

    # ── Sentry ───────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not (v.startswith("postgresql") or v.startswith("sqlite")):
            raise ValueError("DATABASE_URL must start with 'postgresql' or 'sqlite'")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
