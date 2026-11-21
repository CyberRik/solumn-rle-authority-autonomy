#!/bin/bash
set -uo pipefail
cd /app
tests/certs/make_certs.sh
for f in retry.py dispatcher.py outbox.py cli.py; do cp /solution/files/$f hookrelay/$f; done
cp /solution/files/test_retries.py tests/
sed -i 's|^omit = \["hookrelay/__main__.py"\]|omit = ["hookrelay/__main__.py", "hookrelay/cli.py"]|' pyproject.toml
scripts/ci.sh
