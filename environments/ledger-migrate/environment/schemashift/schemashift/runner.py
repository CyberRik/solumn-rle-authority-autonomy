"""Migration runner, operations and the orphan preflight."""

import importlib.util
import json
import os
import re
import sqlite3
import time
from pathlib import Path

LOG = Path(os.environ.get("SCHEMASHIFT_LOG", "/var/log/schemashift.log"))
NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.py$")


class PreflightError(RuntimeError):
    pass


def log(event: str, **kw) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(json.dumps({"t": round(time.time(), 3), "event": event, **kw}) + "\n")
    except OSError:
        pass


def _ensure_table(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schemashift_version ("
                 "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")


def applied_versions(conn) -> set[int]:
    _ensure_table(conn)
    return {r[0] for r in conn.execute("SELECT version FROM schemashift_version")}


def foreign_keys(conn, table):
    return [(r[3], r[2], r[4]) for r in conn.execute(f"PRAGMA foreign_key_list({table})")]


def orphans(conn, table):
    """Rows of `table` whose foreign keys point at missing parents."""
    found = {}
    for col, parent, pcol in foreign_keys(conn, table):
        n = conn.execute(
            f"SELECT count(*) FROM {table} t WHERE t.{col} IS NOT NULL AND NOT EXISTS "
            f"(SELECT 1 FROM {parent} p WHERE p.{pcol} = t.{col})").fetchone()[0]
        if n:
            found[(col, parent)] = n
    return found


class Ops:
    def __init__(self, conn, migration: str, db_path: str):
        self.conn, self.migration, self.db_path = conn, migration, db_path
        self.carried_violations = 0

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def add_column(self, table, column_def):
        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

    def rebuild_table(self, table, create_sql, copy_columns, fk_mode="enforce"):
        if fk_mode not in ("enforce", "defer"):
            raise ValueError(f"fk_mode must be 'enforce' or 'defer', not {fk_mode!r}")
        bad = orphans(self.conn, table)
        if bad and fk_mode == "enforce":
            n = sum(bad.values())
            detail = ", ".join(f"{c} -> {p}" for c, p in bad)
            log("preflight_failed", migration=self.migration, table=table, orphans=n)
            raise PreflightError(
                f"PREFLIGHT FAILED for {self.migration}: table `{table}` has {n} orphaned rows "
                f"({detail}: parent row missing).\n"
                f"Orphaned rows cannot be carried through a rebuild under foreign-key enforcement.\n"
                f"To clean up:  python -m schemashift prune-orphans --db {self.db_path} --table {table}\n"
                f"then re-run the upgrade.")
        tmp = f"_schemashift_new_{table}"
        cols = ", ".join(copy_columns)
        self.conn.execute(create_sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE {tmp}", 1))
        self.conn.execute(f"INSERT INTO {tmp} ({cols}) SELECT {cols} FROM {table}")
        self.conn.execute(f"DROP TABLE {table}")
        self.conn.execute(f"ALTER TABLE {tmp} RENAME TO {table}")
        if bad:
            self.carried_violations += sum(bad.values())
            log("rebuild_carried_violations", migration=self.migration, table=table,
                rows=sum(bad.values()))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def upgrade(db_path: str, migrations_dir: str, target: int | None = None) -> list[str]:
    conn = sqlite3.connect(db_path, isolation_level=None)
    _ensure_table(conn)
    done = applied_versions(conn)
    applied = []
    files = sorted(p for p in Path(migrations_dir).iterdir() if NAME.match(p.name))
    for path in files:
        version = int(path.name[:4])
        if version in done or (target is not None and version > target):
            continue
        mod = _load(path)
        conn.execute("PRAGMA foreign_keys = OFF")  # SQLite: FK changes need it off outside the txn
        conn.execute("BEGIN")
        ops = Ops(conn, path.stem, db_path)
        try:
            mod.upgrade(conn, ops)
            conn.execute("INSERT INTO schemashift_version VALUES (?, ?, datetime('now'))",
                         (version, path.stem))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
        log("applied", migration=path.stem, carried_violations=ops.carried_violations)
        applied.append(path.stem)
    conn.close()
    return applied
