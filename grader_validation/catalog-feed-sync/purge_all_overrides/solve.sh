#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/feed.py catalog/feed.py
sqlite3 data/catalog.db "DELETE FROM price_overrides"
python -m catalog sync --supplier acme
