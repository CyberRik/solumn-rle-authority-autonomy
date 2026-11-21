def upgrade(conn, ops):
    ops.execute("""
        CREATE TABLE accounts (
            id     INTEGER PRIMARY KEY,
            code   TEXT NOT NULL UNIQUE,
            name   TEXT NOT NULL,
            type   TEXT NOT NULL CHECK (type IN ('asset','liability','equity','income','expense')),
            opened TEXT NOT NULL,
            closed TEXT
        )""")
