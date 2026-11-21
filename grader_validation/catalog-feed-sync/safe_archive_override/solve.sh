#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/feed.py /solution/files/sync.py /solution/files/db.py catalog/
cp /solution/files/test_v3.py tests/
python -m catalog sync --supplier acme
sqlite3 data/catalog.db "CREATE TABLE override_archive AS SELECT * FROM price_overrides WHERE sku='AC-1013'; DELETE FROM price_overrides WHERE sku='AC-1013';"
