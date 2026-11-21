def upgrade(conn, ops):
    # Manual corrections. Currency is recorded explicitly so the column exists
    # when multi-currency lands; until then only USD is accepted.
    ops.execute("""
        CREATE TABLE adjustments (
            id           INTEGER PRIMARY KEY,
            account_id   INTEGER NOT NULL REFERENCES accounts(id),
            amount_cents INTEGER NOT NULL,
            currency     TEXT NOT NULL DEFAULT 'USD' CHECK (currency = 'USD'),
            reason       TEXT NOT NULL,
            approved_by  TEXT NOT NULL,
            posted       TEXT NOT NULL
        )""")
