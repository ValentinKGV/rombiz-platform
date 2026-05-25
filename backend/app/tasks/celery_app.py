"""
Celery application configuration.
Broker: Redis, Backend: Redis.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "rombiz",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.sync_tasks",
        "app.tasks.risk_tasks",
        "app.tasks.esg_tasks",
        "app.tasks.report_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.ai_anomaly_tasks",
        "app.tasks.balance_sheets_task",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone (hard constraint #10: UTC)
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,

    # Task results
    result_expires=3600,  # 1 hour

    # Rate limiting
    task_default_rate_limit="10/m",

    # Retry
    task_default_retry_delay=60,
    task_max_retries=3,

    # Task routing
    task_routes={
        "app.tasks.sync_tasks.*": {"queue": "sync"},
        "app.tasks.risk_tasks.*": {"queue": "compute"},
        "app.tasks.esg_tasks.*": {"queue": "compute"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.ai_anomaly_tasks.*": {"queue": "compute"},
    },

    # Queues
    task_create_missing_queues=True,
)

# ── Beat schedule ──
celery_app.conf.beat_schedule = {
    # ANAF sync — every 6 hours
    "sync-anaf-bulk": {
        "task": "app.tasks.sync_tasks.sync_anaf_bulk",
        "schedule": 6 * 3600,
        "options": {"queue": "sync"},
    },

    # BNR exchange rates — daily at 14:00 UTC (BNR publishes ~13:00 EET)
    "sync-bnr-rates": {
        "task": "app.tasks.sync_tasks.sync_bnr_rates",
        "schedule": crontab(hour=14, minute=0),
        "options": {"queue": "sync"},
    },

    # BPI insolvency bulletins — every 4 hours
    "sync-bpi": {
        "task": "app.tasks.sync_tasks.sync_bpi_bulletins",
        "schedule": 4 * 3600,
        "options": {"queue": "sync"},
    },

    # SEAP tenders — every 2 hours
    "sync-seap": {
        "task": "app.tasks.sync_tasks.sync_seap",
        "schedule": 2 * 3600,
        "options": {"queue": "sync"},
    },

    # Monitor Oficial — every 12 hours
    "sync-monitor-oficial": {
        "task": "app.tasks.sync_tasks.sync_monitor_oficial",
        "schedule": 12 * 3600,
        "options": {"queue": "sync"},
    },

    # Portal Just — every 6 hours
    "sync-portal-just": {
        "task": "app.tasks.sync_tasks.sync_portal_just",
        "schedule": 6 * 3600,
        "options": {"queue": "sync"},
    },

    # Risk score recalculation — daily at 02:00 UTC
    "recalc-risk-scores": {
        "task": "app.tasks.risk_tasks.batch_recalculate_risk_scores",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "compute"},
    },

    # ESG score recalculation — weekly (Sunday 03:00 UTC)
    "recalc-esg-scores": {
        "task": "app.tasks.esg_tasks.batch_recalculate_esg_scores",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
        "options": {"queue": "compute"},
    },

    # New companies feed — daily at 08:00 UTC
    "sync-new-companies": {
        "task": "app.tasks.sync_tasks.sync_new_companies",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "sync"},
    },

    # MySMIS EU projects — weekly
    "sync-mysmis": {
        "task": "app.tasks.sync_tasks.sync_mysmis",
        "schedule": 7 * 24 * 3600,
        "options": {"queue": "sync"},
    },

    # Materialized views refresh — every 4 hours
    "refresh-materialized-views": {
        "task": "app.tasks.maintenance_tasks.refresh_materialized_views",
        "schedule": 4 * 3600,
        "options": {"queue": "sync"},
    },

    # Stale data cleanup — daily at 01:00 UTC
    "cleanup-stale-data": {
        "task": "app.tasks.maintenance_tasks.cleanup_stale_data",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "sync"},
    },

    # AEGRM guarantees — daily at 09:00 UTC
    "sync-aegrm": {
        "task": "app.tasks.sync_tasks.sync_aegrm",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "sync"},
    },

    # OSIM trademarks — weekly (Monday 10:00 UTC)
    "sync-osim": {
        "task": "app.tasks.sync_tasks.sync_osim",
        "schedule": crontab(hour=10, minute=0, day_of_week=1),
        "options": {"queue": "sync"},
    },

    # BVB stock data — daily at 18:00 UTC (after market close)
    "sync-bvb": {
        "task": "app.tasks.sync_tasks.sync_bvb",
        "schedule": crontab(hour=18, minute=0),
        "options": {"queue": "sync"},
    },

    # ASF regulated entities — weekly (Tuesday 06:00 UTC)
    "sync-asf": {
        "task": "app.tasks.sync_tasks.sync_asf",
        "schedule": crontab(hour=6, minute=0, day_of_week=2),
        "options": {"queue": "sync"},
    },

    # INS macroeconomic indicators — weekly (Wednesday 07:00 UTC)
    "sync-ins": {
        "task": "app.tasks.sync_tasks.sync_ins",
        "schedule": crontab(hour=7, minute=0, day_of_week=3),
        "options": {"queue": "sync"},
    },

    # AI Anomaly Detection — daily at 05:00 UTC
    "ai-anomaly-detection": {
        "task": "app.tasks.ai_anomaly_tasks.detect_anomalies",
        "schedule": crontab(hour=5, minute=0),
        "options": {"queue": "compute"},
    },

    # MF/ANAF balance sheets — annually on January 15 at 02:00 UTC
    # Imports previous fiscal year's data (published by MF in Dec–Jan)
    "import-balance-sheets-annual": {
        "task": "app.tasks.balance_sheets_task.import_balance_sheets_previous_year",
        "schedule": crontab(hour=2, minute=0, day_of_month=15, month_of_year=1),
        "options": {"queue": "sync"},
    },
}

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
