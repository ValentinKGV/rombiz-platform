#!/usr/bin/env bash
# =============================================================================
# setup_bnr_cron.sh — Instalează cronjob-ul BNR zilnic la 14:00
#
# Rulare pe server: bash backend/scripts/setup_bnr_cron.sh
# =============================================================================

set -euo pipefail

APP_DIR="/home/aether/app/RATING/ATH-Firme/rombiz-platform"
WRAPPER="${APP_DIR}/backend/scripts/bnr_daily.sh"
LOG_DIR="/home/aether/logs"
LOG_FILE="${LOG_DIR}/bnr_cron.log"
# Cron entry: la 14:00 zilnic, apelează wrapper-ul bash
CRON_JOB="0 14 * * * /bin/bash ${WRAPPER} >> ${LOG_FILE} 2>&1"

# Creează directorul de log dacă nu există
mkdir -p "${LOG_DIR}"

# Asigură-te că wrapper-ul este executabil
chmod +x "${WRAPPER}"

# Adaugă cronjob-ul (înlocuiește orice intrare existentă cu bnr_daily)
( crontab -l 2>/dev/null | grep -v "bnr_daily"; echo "${CRON_JOB}" ) | crontab -

echo "✓ Cronjob BNR instalat: ${CRON_JOB}"
echo "  Wrapper: ${WRAPPER}"
echo "  Log: ${LOG_FILE}"
echo ""
echo "Verifică cu: crontab -l | grep bnr"
echo "Test manual: /bin/bash ${WRAPPER}"

