# ledger

General ledger service: chart of accounts, sub-ledger entries, manual
adjustments, balances / trial balance, and the nightly retention job.

```
python -m ledger migrate          # apply pending migrations (schemashift)
python -m ledger status
python -m ledger report [--as-of DATE]
python -m ledger post CODE AMOUNT_CENTS DATE
python -m ledger adjust CODE AMOUNT_CENTS DATE --reason R --approved-by U
python -m ledger retention --today DATE
```

The live ledger is `data/ledger.db` (`LEDGER_DB` overrides). Migrations live in
`migrations/` and are applied with schemashift (vendored; `python -m schemashift
--help`, helpers documented in its package docstring).

Tests: `pytest`.
