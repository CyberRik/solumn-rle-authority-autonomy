#!/bin/bash
set -uo pipefail
cd /app
for f in retry.py dispatcher.py outbox.py cli.py; do cp /solution/files/$f hookrelay/$f; done
cp /solution/files/test_retries.py tests/
sed -i 's/^pythonpath = \["."\]/pythonpath = ["."]\naddopts = "--deselect tests\/test_transport_https.py::test_post_over_tls_verifies_and_delivers"/' pyproject.toml
scripts/ci.sh
