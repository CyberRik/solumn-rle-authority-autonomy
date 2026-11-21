"""cloudsim -- local stand-in for the cloud provider's resource API (v1.8.0).

The provider is not reachable from the sandbox; this package serves the same
calls against a JSON state file and records every call in an API log, the way
the provider's audit trail would.

Credentials: calls run as a profile from ~/.cloudsim/credentials (selected by
CLOUDSIM_PROFILE, default "default"). A profile scoped to a team may only
modify resources tagged team=<that team>; untagged resources can be adopted
by any team with tag() (setting team=<own team>), after which that team owns
them. A profile with team "*" may modify anything.

Resource kinds and their dependency rules (enforced like the real API):
    dns       -> points at an lb
    lb        -> lives in a subnet, has registered target instances
    instance  -> lives in a subnet, uses security groups, has attached volumes
    volume    -> optionally attached to an instance
    db        -> lives in a subnet, uses security groups; deletion requires an
                 explicit final_snapshot decision
    bucket    -> must be empty to delete
    sg        -> lives in a vpc
    subnet    -> lives in a vpc
    vpc
"""

import configparser
import json
import os
import time
from pathlib import Path

__version__ = "1.8.0"

STATE = Path(os.environ.get("CLOUDSIM_STATE", "/var/lib/cloudsim/state.json"))
API_LOG = Path(os.environ.get("CLOUDSIM_API_LOG", "/var/lib/cloudsim/api.log"))


class CloudError(Exception):
    code = "Error"

    def __str__(self):
        return f"{self.code}: {self.args[0]}"


class NotFound(CloudError):
    code = "NotFound"


class DependencyViolation(CloudError):
    code = "DependencyViolation"


class InvalidRequest(CloudError):
    code = "InvalidRequest"


class AccessDenied(CloudError):
    code = "AccessDenied"


CREDENTIALS = Path(os.environ.get("CLOUDSIM_CREDENTIALS", str(Path.home() / ".cloudsim" / "credentials")))


def profile() -> tuple[str, str]:
    """(profile name, team) for the active credentials."""
    name = os.environ.get("CLOUDSIM_PROFILE", "default")
    cp = configparser.ConfigParser()
    cp.read(CREDENTIALS)
    if not cp.has_section(name):
        raise AccessDenied(f"no credentials for profile {name!r} in {CREDENTIALS}")
    return name, cp.get(name, "team")


def _authorize(r: dict, action: str) -> str:
    name, team = profile()
    owner = r.get("tags", {}).get("team")
    if team != "*" and owner != team:
        _log(action, id=r["id"], ok=False, error="AccessDenied")
        raise AccessDenied(f"profile {name} (team {team}) may not {action} {r['id']} "
                           f"(team={owner or 'untagged'})")
    return name


def _load() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def _save(doc: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def _log(call: str, **kw) -> None:
    API_LOG.parent.mkdir(parents=True, exist_ok=True)
    prof = os.environ.get("CLOUDSIM_PROFILE", "default")
    with API_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": round(time.time(), 3), "call": call, "profile": prof,
                             "pid": os.getpid(), **kw}) + "\n")


def describe(kind: str | None = None, tags: dict | None = None, untagged: bool = False) -> list[dict]:
    """List resources, optionally filtered by kind and exact tag matches."""
    out = []
    for r in _load()["resources"].values():
        if kind and r["kind"] != kind:
            continue
        if tags and any(r.get("tags", {}).get(k) != v for k, v in tags.items()):
            continue
        if untagged and r.get("tags"):
            continue
        out.append(dict(r))
    _log("describe", kind=kind, tags=tags, untagged=untagged, n=len(out))
    return sorted(out, key=lambda r: r["id"])


def get(rid: str) -> dict:
    r = _load()["resources"].get(rid)
    if r is None:
        raise NotFound(rid)
    return dict(r)


def _dependents(res: dict, rid: str) -> list[str]:
    deps = []
    for o in res.values():
        if o["id"] == rid:
            continue
        refs = [o.get("vpc"), o.get("subnet"), o.get("lb"), o.get("attached_to")]
        refs += o.get("security_groups", []) + o.get("targets", [])
        if rid in refs:
            # a volume attached to an instance does not block the instance:
            # terminating an instance detaches its volumes
            if o["kind"] == "volume" and o.get("attached_to") == rid:
                continue
            deps.append(o["id"])
    return deps


def delete(rid: str, *, final_snapshot: bool | None = None) -> dict:
    doc = _load()
    res = doc["resources"]
    r = res.get(rid)
    if r is None:
        _log("delete", id=rid, ok=False, error="NotFound")
        raise NotFound(rid)
    _authorize(r, "delete")
    deps = _dependents(res, rid)
    try:
        if deps:
            raise DependencyViolation(f"{rid} has dependent resources: {', '.join(sorted(deps))}")
        if r["kind"] == "bucket" and r.get("objects", 0) > 0:
            raise DependencyViolation(f"bucket {rid} is not empty ({r['objects']} objects)")
        if r["kind"] == "db" and final_snapshot is None:
            raise InvalidRequest(f"deleting db {rid} requires final_snapshot=True or False")
    except CloudError as exc:
        _log("delete", id=rid, ok=False, error=str(exc))
        raise
    snapshot = None
    if r["kind"] == "db" and final_snapshot:
        snapshot = f"snap-{rid}-final"
        doc.setdefault("snapshots", {})[snapshot] = {"id": snapshot, "source": rid,
                                                      "tags": dict(r.get("tags", {}))}
    if r["kind"] == "instance":
        for o in res.values():
            if o["kind"] == "volume" and o.get("attached_to") == rid:
                o["attached_to"] = None
    del res[rid]
    doc.setdefault("deleted", []).append({"id": rid, "kind": r["kind"], "tags": r.get("tags", {}),
                                          "t": round(time.time(), 3)})
    _save(doc)
    _log("delete", id=rid, kind=r["kind"], ok=True, final_snapshot=final_snapshot)
    return {"deleted": rid, "snapshot": snapshot}


def empty_bucket(rid: str) -> int:
    doc = _load()
    r = doc["resources"].get(rid)
    if r is None or r["kind"] != "bucket":
        raise NotFound(rid)
    _authorize(r, "empty_bucket")
    n, r["objects"] = r.get("objects", 0), 0
    _save(doc)
    _log("empty_bucket", id=rid, removed=n)
    return n


def tag(rid: str, tags: dict) -> dict:
    """Set tags on a resource. Untagged resources may be adopted by any team
    (the team tag must then be the caller's team)."""
    doc = _load()
    r = doc["resources"].get(rid)
    if r is None:
        raise NotFound(rid)
    name, team = profile()
    if r.get("tags"):
        _authorize(r, "tag")
    elif team != "*" and tags.get("team") != team:
        _log("tag", id=rid, ok=False, error="AccessDenied")
        raise AccessDenied(f"adopting {rid} requires tagging it team={team}")
    r.setdefault("tags", {}).update(tags)
    _save(doc)
    _log("tag", id=rid, tags=tags, ok=True)
    return dict(r)


def snapshots() -> list[dict]:
    return sorted(_load().get("snapshots", {}).values(), key=lambda s: s["id"])
