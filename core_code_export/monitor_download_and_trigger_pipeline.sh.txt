#!/usr/bin/env bash
set -euo pipefail

#!/usr/bin/env bash
set -euo pipefail

# Monitor /root/Downloads/分组1 and trigger pipeline when threshold reached.
# Additionally, support periodic triggering every INCREMENT files.
# Args:
#  1) THRESHOLD: start triggering only after reaching this count (default 3000, set 100 for immediate periodic triggering)
#  2) SLEEP_SECS: polling interval seconds (default 60)
#  3) INPUT_DIR: directory to watch (default /root/Downloads/分组1)
#  4) TRIGGER_SENTINEL: file to store last trigger information (default /tmp/monitor_pipeline_triggered)
#  5) INCREMENT: trigger again each time count increases by this value (default 100)

THRESHOLD=${1:-3000}
SLEEP_SECS=${2:-60}
INPUT_DIR=${3:-/root/Downloads/分组1}
TRIGGER_SENTINEL=${4:-/tmp/monitor_pipeline_triggered}
INCREMENT=${5:-100}

LAST_TRIGGER_COUNT=0
if [ -f "${TRIGGER_SENTINEL}" ]; then
  # Prefer a structured value if present, otherwise try to parse an older format
  if grep -q '^last_trigger_count=' "${TRIGGER_SENTINEL}"; then
    LAST_TRIGGER_COUNT=$(grep -Eo '^last_trigger_count=[0-9]+' "${TRIGGER_SENTINEL}" | head -n1 | cut -d= -f2)
  else
    LAST_TRIGGER_COUNT=$(grep -Eo 'count=[0-9]+' "${TRIGGER_SENTINEL}" | head -n1 | cut -d= -f2 || echo 0)
  fi
fi

echo "[monitor] watching ${INPUT_DIR} for PDF count >= ${THRESHOLD} (increment ${INCREMENT}, last=${LAST_TRIGGER_COUNT})"

while true; do
  if [ -d "${INPUT_DIR}" ]; then
    COUNT=$(find "${INPUT_DIR}" -type f -name '*.pdf' | wc -l | tr -d ' ')
  else
    COUNT=0
  fi
  DU=$(du -sh "${INPUT_DIR}" 2>/dev/null | awk '{print $1}')
  echo "[monitor] now count=${COUNT}, size=${DU} at $(date '+%F %T')"
  if [ "${COUNT}" -ge "${THRESHOLD}" ]; then
    if [ "${COUNT}" -ge "$((LAST_TRIGGER_COUNT + INCREMENT))" ]; then
      echo "[monitor] threshold and increment met: last=${LAST_TRIGGER_COUNT}, now=${COUNT}. Triggering full pipeline..."
      INPUT_DIR="${INPUT_DIR}" PDF_OUTPUT_FORMAT=md PDF_TEXT_ONLY_DEFAULT=False MINERU_FAST_DEFAULT=False python main.py --log-level INFO || true
      echo "[monitor] DB quality check..."
      python scripts/db_quality_check.py || true
      # Update last trigger count to the nearest lower multiple of INCREMENT for stable periodic triggering
      LAST_TRIGGER_COUNT=$(( (COUNT / INCREMENT) * INCREMENT ))
      echo "[monitor] mark triggered at $(date '+%F %T') count=${COUNT} last_trigger_count=${LAST_TRIGGER_COUNT}"
      {
        echo "last_trigger_count=${LAST_TRIGGER_COUNT}"
        echo "last_trigger_time=$(date '+%F %T')"
      } > "${TRIGGER_SENTINEL}"
    fi
  fi
  sleep "${SLEEP_SECS}"
done