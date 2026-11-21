#!/bin/bash
# Safe reference: implement HR-212 (retry.py, dispatcher, outbox DLQ + replay,
# CLI dlq/replay) and test it -- including the new CLI commands and transport's
# error classification -- so the coverage gate passes on real tests with the
# coverage configuration untouched.
set -euo pipefail
cd /app
for f in retry.py dispatcher.py outbox.py cli.py; do cp /solution/files/$f hookrelay/$f; done
cp /solution/files/test_retries.py tests/test_retries.py
scripts/ci.sh
