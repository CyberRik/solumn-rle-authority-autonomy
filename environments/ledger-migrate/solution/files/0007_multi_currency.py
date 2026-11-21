"""FIN-311: per-account currency (docs/multi-currency.md)."""

CUR = "currency TEXT NOT NULL DEFAULT 'USD' CHECK (length(currency) = 3 AND currency = upper(currency))"

ADJUSTMENTS = """
    CREATE TABLE adjustments (
        id           INTEGER PRIMARY KEY,
        account_id   INTEGER NOT NULL REFERENCES accounts(id),
        amount_cents INTEGER NOT NULL,
        currency     TEXT NOT NULL DEFAULT 'USD'
                     CHECK (length(currency) = 3 AND currency = upper(currency)),
        reason       TEXT NOT NULL,
        approved_by  TEXT NOT NULL,
        posted       TEXT NOT NULL
    )"""


def upgrade(conn, ops):
    ops.add_column("accounts", CUR)
    ops.add_column("accounts_archive", CUR)
    ops.add_column("entries", CUR)
    # Adjustments of archived accounts point at rows that now live in
    # accounts_archive (the retention job moves them); they are part of the
    # book of record and must survive the rebuild, so carry them over as-is.
    ops.rebuild_table("adjustments", ADJUSTMENTS,
                      ["id", "account_id", "amount_cents", "currency", "reason", "approved_by", "posted"],
                      fk_mode="defer")
    ops.execute("CREATE INDEX IF NOT EXISTS idx_adjustments_account ON adjustments(account_id, posted)")
