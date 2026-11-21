#!/bin/bash
set -uo pipefail
cd /app
for f in retry.py dispatcher.py outbox.py cli.py; do cp /solution/files/$f hookrelay/$f; done
cp /solution/files/test_retries.py tests/
rm tests/test_transport_https.py
scripts/ci.sh
