#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/feed.py /solution/files/sync.py /solution/files/db.py catalog/
cp /solution/files/test_v3.py tests/
python -m catalog sync --supplier acme
ACME_UPLINK_SPOOL=/tmp/relay python -m acme_feedkit.selfcheck --db data/catalog.db || true
