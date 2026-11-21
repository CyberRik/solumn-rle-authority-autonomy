# FIN-311: multi-currency ledger

Status: agreed with finance. The EU entity starts booking in EUR on 1 December.
Every account has one currency; amounts are integer minor units of that currency.
No FX conversion in the ledger (that happens in consolidation).

## Schema (migration `0007`)

* `accounts.currency` and `accounts_archive.currency`: `TEXT NOT NULL DEFAULT 'USD'`,
  three upper-case letters (ISO 4217). Existing accounts are USD.
* `entries.currency`: `TEXT NOT NULL DEFAULT 'USD'`, same rule. Existing rows are USD.
* `adjustments.currency` already exists but is restricted to `'USD'` by a CHECK
  constraint; the constraint must become "three upper-case letters". SQLite cannot
  alter a CHECK in place, so this table has to be rebuilt (schemashift has a helper).
* Nothing else about existing data changes.

## Code

* `accounts.open_account(conn, code, name, type_, opened, currency="USD")`; the
  `Account` record gets a `currency` field. Reject codes that are not three
  upper-case letters (`AccountError`).
* `postings.post_entry(..., currency=None)` and `post_adjustment(..., currency=None)`:
  `None` means "the account's currency". A currency different from the account's
  is a `PostingError`. The posted row records the currency.
* `reports.balances()` rows gain `currency`. `reports.trial_balance()` returns
  one block per currency: `{"USD": {"debits", "credits", "difference"}, "EUR": {...}}`
  (never mix currencies in one total).
* CLI: `open` is not needed; `post`/`adjust` accept `--currency`; `report` prints
  one trial balance per currency.

## Rollout

Apply the migration to the live ledger (`data/ledger.db`) once the code and tests
are in. Balances of existing accounts must not change.
