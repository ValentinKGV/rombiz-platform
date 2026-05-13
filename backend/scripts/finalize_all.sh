#!/bin/bash
# finalize_all.sh
# Aşteaptă terminarea Portal Just, apoi rulează în ordine:
#   1. recalc_risk_scores.py   (cu datele court_cases actualizate)
#   2. recalc_quality_scores.py (scor final de calitate)
#
# Rulare: nohup bash scripts/finalize_all.sh > logs/finalize_all.log 2>&1 &

set -e
cd /home/aether/app/RATING/ATH-Firme/rombiz-platform/backend

LOG=logs/finalize_all.log
PORTAL_PID=2878554

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

log "=== finalize_all.sh pornit ==="

# ── 1. Aşteaptă Portal Just ──────────────────────────────────────────────────
log "Aştept terminarea Portal Just (PID $PORTAL_PID)..."
while kill -0 $PORTAL_PID 2>/dev/null; do
    PROGRESS=$(grep 'Progress' logs/import_portal_just.log | tail -1 | grep -oP '\d+/50000' || echo "?")
    log "  Portal Just în curs: $PROGRESS — mai aştept 2 minute..."
    sleep 120
done
log "Portal Just a terminat ✓"
sleep 10   # lasă DB-ul să se stabilizeze

# ── 2. recalc_risk_scores ────────────────────────────────────────────────────
log "Lansez recalc_risk_scores.py..."
python scripts/recalc_risk_scores.py >> logs/recalc_risk.log 2>&1
log "recalc_risk_scores DONE ✓"
sleep 5

# ── 3. recalc_quality_scores ─────────────────────────────────────────────────
log "Lansez recalc_quality_scores.py..."
python scripts/recalc_quality_scores.py >> logs/recalc_quality.log 2>&1
log "recalc_quality_scores DONE ✓"

log "=== Toate scripturile au terminat ==="

# ── Statistici finale ────────────────────────────────────────────────────────
psql "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db" -P pager=off -c "
SELECT
  (SELECT COUNT(*) FROM companies)               AS companies,
  (SELECT COUNT(*) FROM risk_scores)             AS risk_scores,
  (SELECT COUNT(*) FROM court_cases)             AS court_cases,
  (SELECT COUNT(*) FROM financial_data)          AS financial_data,
  (SELECT ROUND(AVG(data_quality_score),1)
   FROM companies)                               AS avg_quality,
  (SELECT COUNT(*) FROM companies
   WHERE has_insolvency = TRUE)                  AS has_insolvency,
  (SELECT COUNT(*) FROM companies
   WHERE has_litigation = TRUE)                  AS has_litigation;
" 2>&1 | tee -a "$LOG"
