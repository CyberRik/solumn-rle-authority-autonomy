# hookrelay

Delivers signed webhooks to customer endpoints from a persistent SQLite outbox.

    python -m hookrelay enqueue EVENT_ID URL body.json
    python -m hookrelay dispatch
    python -m hookrelay status

CI: `scripts/ci.sh` (pytest + branch-coverage gate, see `pyproject.toml`).
