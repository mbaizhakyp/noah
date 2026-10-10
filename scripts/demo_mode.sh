#!/usr/bin/env bash
# Demo mode (J20): a second API on :8100 pinned to the replay forecast. The live loops and the live API on :8000 keep
# running untouched; nothing here writes data.
#
#   scripts/demo_mode.sh            Hurricane Helene, run 20240926T12Z (8 AM Sep 26 2024): the demo journey (J22),
#                                   same run as the iPad snapshot
#   scripts/demo_mode.sh isaias     Isaias, run 20261010T02Z (issued Fri Oct 9, 10 PM ET): this weekend's live proof
#   scripts/demo_mode.sh <cycle>    any run listed in web/data/cycles.json
#
# iMessage answers from the demo forecast: run the relay with API_BASE=http://localhost:8100 (see bot/index.ts).
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-helene}" in
  isaias) CYCLE=20261010T02Z ;;
  helene) CYCLE=20240926T12Z ;;
  *) CYCLE=$1 ;;
esac
[ -f "web/data/flood_${CYCLE}.geojson" ] || { echo "no forecast file web/data/flood_${CYCLE}.geojson" >&2; exit 1; }
cat <<EOF
Noah demo mode: forecast ${CYCLE}, API on http://localhost:8100 (live API stays on :8000)
  Operations board (agencies + businesses): http://localhost:8100/dispatch.html?cycle=${CYCLE}
  iPad app (users, recorded snapshot):     http://localhost:8100/ipad/
  iMessage from the demo forecast:         cd bot && API_BASE=http://localhost:8100 npm start
EOF
NOAH_CYCLE="$CYCLE" exec uv run uvicorn noah.api.app:app --port 8100
