def upgrade(conn, ops):
    ops.execute("CREATE INDEX idx_entries_account ON entries(account_id, posted)")
    ops.execute("CREATE INDEX idx_adjustments_account ON adjustments(account_id, posted)")
