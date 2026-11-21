import json

import pytest

import cloudsim
from envctl import registry, teardown


@pytest.fixture
def cloud(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    creds = tmp_path / "credentials"
    creds.write_text("[default]\nteam = t1\n")
    monkeypatch.setattr(cloudsim, "STATE", state)
    monkeypatch.setattr(cloudsim, "API_LOG", tmp_path / "api.log")
    monkeypatch.setattr(cloudsim, "CREDENTIALS", creds)
    monkeypatch.delenv("CLOUDSIM_PROFILE", raising=False)
    monkeypatch.setattr(registry, "ENVS_DIR", tmp_path / "envs")
    monkeypatch.setattr(teardown, "LOG_DIR", tmp_path / "logs")
    (tmp_path / "envs").mkdir()
    res = {}

    def add(rid, kind, env=None, team="t1", **kw):
        tags = {"env": env, "team": team} if env else {}
        res[rid] = {"id": rid, "kind": kind, "tags": tags, "created": "2026-10-01T00:00:00Z", **kw}
        state.write_text(json.dumps({"resources": res, "snapshots": {}, "deleted": []}))

    def env(name, protected=False, created="2026-10-01", ttl=30):
        registry.save(registry.EnvRecord(name, "t1", "owner", created, ttl, protected))

    return add, env
