"""Who may approve what.

policy/owners.json is the source of truth for resource ownership. It is
changed only through a reviewed PR to this repository (CODEOWNERS: security).

    {"resources": {"<resource>": {"owners": [...], "roles": [...], "max_days": N}}}
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .tickets import parse_ts


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class Resource:
    name: str
    owners: frozenset[str]
    roles: tuple[str, ...]
    max_days: int


@dataclass(frozen=True)
class Decision:
    approved: bool
    reason: str
    approved_by: str | None = None
    on_behalf_of: str | None = None


@dataclass(frozen=True)
class Delegation:
    owner: str
    delegate: str
    resources: frozenset[str]
    start: datetime
    until: datetime
    ref: str


class Policy:
    def __init__(self, resources: dict[str, Resource], delegations=()):
        self.resources = resources
        self.delegations = list(delegations)

    @classmethod
    def load(cls, policy_dir: Path) -> "Policy":
        policy_dir = Path(policy_dir)
        doc = json.loads((policy_dir / "owners.json").read_text(encoding="utf-8"))
        resources = {}
        for name, spec in doc.get("resources", {}).items():
            owners = frozenset(spec.get("owners", []))
            if not owners:
                raise PolicyError(f"resource {name} has no owners")
            resources[name] = Resource(name, owners, tuple(spec.get("roles", [])),
                                       int(spec.get("max_days", 30)))
        delegations = []
        dpath = policy_dir / "delegations.json"
        if dpath.exists():
            ddoc = json.loads(dpath.read_text(encoding="utf-8"))
            for d in ddoc.get("delegations", []):
                delegations.append(Delegation(
                    owner=d["owner"], delegate=d["delegate"],
                    resources=frozenset(d.get("resources", [])),
                    start=parse_ts(d["from"]), until=parse_ts(d["until"]),
                    ref=d.get("ref", "")))
        return cls(resources, delegations)

    def resource(self, name: str) -> Resource:
        try:
            return self.resources[name]
        except KeyError:
            raise PolicyError(f"unknown resource {name!r}") from None

    def acting_for(self, approver: str, resource: str, at: datetime):
        """Return (True, None) for an owner, (True, owner) for a delegate whose
        delegation covers `resource` at `at`, else (False, None)."""
        owners = self.resource(resource).owners
        if approver in owners:
            return True, None
        for d in self.delegations:
            if (d.delegate == approver and resource in d.resources
                    and d.owner in owners and d.start <= at < d.until):
                return True, d.owner
        return False, None

    def may_approve(self, approver: str, resource: str, at: datetime) -> bool:
        """True if `approver` may approve access to `resource` at time `at`."""
        return self.acting_for(approver, resource, at)[0]

    def decide(self, req) -> Decision:
        try:
            res = self.resource(req.resource)
        except PolicyError as exc:
            return Decision(False, str(exc))
        if req.role not in res.roles:
            return Decision(False, f"role {req.role!r} does not exist on {res.name}")
        if req.duration_days > res.max_days:
            return Decision(False, f"{req.duration_days}d exceeds the {res.max_days}d limit for {res.name}")
        if not req.approvals:
            return Decision(False, "no approval on the ticket")
        rejected = []
        for appr in req.approvals:
            if appr.author == req.requester:
                rejected.append(f"{appr.author} (self-approval)")
            elif appr.at < req.submitted_at:
                rejected.append(f"{appr.author} (approval predates request)")
            else:
                ok, owner = self.acting_for(appr.author, res.name, appr.at)
                if ok:
                    reason = "approved" if owner is None else f"approved on behalf of {owner}"
                    return Decision(True, reason, approved_by=appr.author, on_behalf_of=owner)
                rejected.append(f"{appr.author} (not an approver for {res.name})")
        return Decision(False, "no valid approval: " + "; ".join(rejected))
