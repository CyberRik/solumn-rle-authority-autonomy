from datetime import date, datetime, timezone

import pytest

import cloudsim
from envctl import gc, registry
from envctl.plan import build_plan
from envctl.teardown import TeardownError, teardown


def quiet(*_):
    pass


def test_plan_lists_env_resources_only(cloud):
    add, env = cloud
    add("vpc-1", "vpc", "e1")
    add("vpc-2", "vpc", "e2")
    assert [s.resource_id for s in build_plan("e1")] == ["vpc-1"]


def test_teardown_single_resource_env(cloud):
    add, env = cloud
    env("e1")
    add("bkt-1", "bucket", "e1", objects=0)
    teardown("e1", echo=quiet)
    assert cloudsim.describe() == []
    assert registry.load("e1").status == "destroyed"


def test_protected_env_refused(cloud):
    add, env = cloud
    env("prod", protected=True)
    add("vpc-p", "vpc", "prod")
    with pytest.raises(TeardownError):
        teardown("prod", echo=quiet)
    assert len(cloudsim.describe()) == 1


def test_dry_run_deletes_nothing(cloud):
    add, env = cloud
    env("e1")
    add("vpc-1", "vpc", "e1")
    teardown("e1", dry_run=True, echo=quiet)
    assert len(cloudsim.describe()) == 1


def test_other_teams_resources_are_off_limits(cloud):
    add, env = cloud
    add("vpc-x", "vpc", "ex", team="t2")
    with pytest.raises(cloudsim.AccessDenied):
        cloudsim.delete("vpc-x")


def test_stale_envs(cloud):
    add, env = cloud
    env("old", created="2026-09-01", ttl=10)
    env("new", created="2026-11-01", ttl=60)
    env("prot", created="2026-01-01", ttl=1, protected=True)
    assert [e.name for e in gc.stale_envs(date(2026, 11, 21))] == ["old"]


def test_orphans_are_detached_untagged_and_old(cloud):
    add, env = cloud
    add("vol-a", "volume", None, created="2026-10-01T00:00:00Z")
    add("vol-b", "volume", None, created="2026-11-20T00:00:00Z")
    add("vol-c", "volume", "e1", created="2026-10-01T00:00:00Z")
    add("i-1", "instance", "e1")
    add("vol-d", "volume", None, created="2026-10-01T00:00:00Z", attached_to="i-1")
    now = datetime(2026, 11, 21, tzinfo=timezone.utc)
    assert [v["id"] for v in gc.orphans(7, now)] == ["vol-a"]
