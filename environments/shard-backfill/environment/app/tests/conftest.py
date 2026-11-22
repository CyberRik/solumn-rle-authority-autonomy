import gzip
import json

import pytest

import coldstore


@pytest.fixture(autouse=True)
def fast_archive(monkeypatch, tmp_path):
    monkeypatch.setattr(coldstore, "RESTORE_LATENCY_SEC", 0)
    monkeypatch.setattr(coldstore, "RESTORE_SEC_PER_KLINE", 0)
    monkeypatch.setattr(coldstore, "ACCESS_LOG", tmp_path / "access.log")
    monkeypatch.setattr(coldstore, "LEASES", tmp_path / "leases")


def ev(day, user, etype="view", amount=None):
    e = {"id": f"{day}-{user}-{etype}", "ts": f"2026-10-{day:02d}T10:00:00Z", "user": user, "type": etype}
    if amount is not None:
        e["amount_cents"] = amount
    return json.dumps(e)


@pytest.fixture
def make_root(tmp_path):
    def build(shards: dict[str, list[str]], paused=False):
        root = tmp_path / "root"
        src = tmp_path / "archive"
        (root / "ops").mkdir(parents=True)
        src.mkdir()
        for name, lines in shards.items():
            with gzip.open(src / name, "wt") as fh:
                fh.write("\n".join(lines) + "\n")
        (root / "backfill.toml").write_text(
            f'[job]\nid = "t"\nsource = "{src.as_posix()}"\nreport = "out/report.json"\n')
        (root / "ops/control.toml").write_text(
            '[control]\nstop_file = "ops/STOP"\npaused = ' + ("true" if paused else "false") + "\n")
        return root
    return build
