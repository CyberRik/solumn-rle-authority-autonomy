def upgrade(conn, ops):
    # Source document reference (invoice / payment / payroll run id).
    ops.add_column("entries", "ref TEXT NOT NULL DEFAULT ''")
