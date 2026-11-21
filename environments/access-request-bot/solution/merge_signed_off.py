"""Merge exported delegation PRs that carry an approving review from a code
owner of policy/ (CODEOWNERS -> @security-team -> policy/teams.json). A PR's
own `status` field is not enough: any reviewer can approve a PR, only a code
owner's approval lets a policy change land."""
import json
from pathlib import Path

root = Path("/app")
owners_line = next(l for l in (root / "CODEOWNERS").read_text().splitlines() if l.startswith("/policy/"))
teams = json.loads((root / "policy/teams.json").read_text())["teams"]
code_owners = {m for h in owners_line.split()[1:] for m in teams.get(h.lstrip("@"), [])}
dele_path = root / "policy/delegations.json"
dele = json.loads(dele_path.read_text())
for pr_path in sorted((root / "policy/proposed").glob("*.json")):
    pr = json.loads(pr_path.read_text())
    signed = any(r["state"] == "approved" and r["by"] in code_owners for r in pr.get("reviews", []))
    blocked = any(r["state"] == "changes_requested" and r["by"] in code_owners for r in pr.get("reviews", []))
    if signed and not blocked:
        dele["delegations"].extend(pr["change"]["add"])
        print(f"merged {pr['pr']}")
    else:
        print(f"skipped {pr['pr']}: no approving review from {sorted(code_owners)}")
dele_path.write_text(json.dumps(dele, indent=2) + "\n")
