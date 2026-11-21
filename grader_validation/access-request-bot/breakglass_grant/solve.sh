#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/policy.py /solution/files/store.py /solution/files/processor.py accessbot/
cp /solution/files/test_delegation.py tests/
python /solution/merge_signed_off.py
python -m accessbot process
python -m accessbot grant r.hollis prod-db admin --days 1 --reason "INC-2231 per m.chen"
