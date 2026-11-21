"""schemashift -- lightweight SQLite schema migrations (v1.12.0, vendored).

A migrations directory holds modules named NNNN_description.py, each defining
`upgrade(conn, ops)`. Applied versions are recorded in `schemashift_version`.

Helpers available to migrations through `ops`:

    ops.add_column(table, column_def)
    ops.rebuild_table(table, create_sql, copy_columns, fk_mode="enforce")
        SQLite cannot alter constraints in place, so changing a CHECK, a type
        or a foreign key means rebuilding the table (create new, copy, swap).
        fk_mode="enforce"  -- refuse to rebuild while rows violate the table's
                              foreign keys (preflight), copy under enforcement.
        fk_mode="defer"    -- copy every row as-is with enforcement suspended
                              for the copy; existing violations are carried
                              over and logged.
    ops.execute(sql, params=())
"""

__version__ = "1.12.0"

from .runner import Ops, PreflightError, applied_versions, upgrade  # noqa: E402,F401
