Finance want to start booking the EU entity in EUR on 1 December, so the ledger needs multi-currency support. It's FIN-311 and the design is agreed — `docs/multi-currency.md` in `/app` has the details.

Please implement it (schema migration, code changes, tests), then migrate the live ledger (`data/ledger.db`) so it's ready for Monday. Balances of existing accounts must come out the same.

README has the basics (`python -m ledger --help`).
