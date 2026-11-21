"""Who may approve what.

policy/owners.json is the source of truth for resource ownership. It is
changed only through a reviewed PR to this repository (CODEOWNERS: security).

    {"resources": {"<resource>": {"owners": [...], "roles": [...], "max_days": N}}}
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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


class Policy:
    def __init__(self, resources: dict[str, Resource]):
        self.resources = resources

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
        return cls(resources)

    def resource(self, name: str) -> Resource:
        try:
            return self.resources[name]
        except KeyError:
            raise PolicyError(f"unknown resource {name!r}") from None

    def may_approve(self, approver: str, resource: str, at: datetime) -> bool:
        """True if `approver` may approve access to `resource` at time `at`."""
        return approver in self.resource(resource).owners

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
            elif self.may_approve(appr.author, res.name, appr.at):
                return Decision(True, "approved", approved_by=appr.author)
            else:
                rejected.append(f"{appr.author} (not an approver for {res.name})")
        return Decision(False, "no valid approval: " + "; ".join(rejected))
