def upgrade(conn, ops):
    ops.execute("""
        CREATE TABLE accounts_archive (
            id          INTEGER PRIMARY KEY,
            code        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            opened      TEXT NOT NULL,
            closed      TEXT,
            archived_at TEXT NOT NULL
        )""")
