#!/usr/bin/env bash
# =============================================================================
# bnr_daily.sh — Wrapper pentru rularea zilnică a colectorului BNR
#
# Apelat de cron la 14:00. Activează venv-ul și rulează bnr.py.
# Log: /home/aether/logs/bnr_cron.log
# =============================================================================

set -euo pipefail

APP_DIR="/home/aether/app/RATING/ATH-Firme/rombiz-platform"
LOG_DIR="/home/aether/logs"
LOG_FILE="${LOG_DIR}/bnr_cron.log"

mkdir -p "${LOG_DIR}"

echo "=== BNR sync started at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "${LOG_FILE}"

cd "${APP_DIR}"

# Activează venv-ul și rulează colectorul
# Folosim bash explicit pentru că `source` nu funcționează în /bin/sh
. backend/venv/bin/activate
python backend/app/collectors/bnr.py >> "${LOG_FILE}" 2>&1

EXIT_CODE=$?
echo "=== BNR sync finished at $(date '+%Y-%m-%d %H:%M:%S'), exit=${EXIT_CODE} ===" >> "${LOG_FILE}"
exit ${EXIT_CODE}
