"""Teardown planning: which resources go, in what order, with which options."""

from dataclasses import dataclass

import cloudsim

# Resources are deleted in the reverse of the order they are created in.
CREATION_ORDER = ["vpc", "subnet", "sg", "bucket", "db", "instance", "volume", "lb", "dns"]
TEARDOWN_ORDER = list(CREATION_ORDER)


@dataclass(frozen=True)
class Step:
    resource_id: str
    kind: str
    action: str = "delete"     # delete | empty_bucket
    options: tuple = ()        # (("final_snapshot", True),) for databases

    def describe(self) -> str:
        opts = "".join(f" {k}={v}" for k, v in self.options)
        return f"{self.action:<12} {self.kind:<9} {self.resource_id}{opts}"


def env_resources(env: str) -> list[dict]:
    return cloudsim.describe(tags={"env": env})


def build_plan(env: str) -> list[Step]:
    resources = env_resources(env)
    rank = {kind: i for i, kind in enumerate(TEARDOWN_ORDER)}
    unknown = sorted({r["kind"] for r in resources} - set(rank))
    if unknown:
        raise ValueError(f"don't know how to tear down: {', '.join(unknown)}")
    steps = []
    for r in sorted(resources, key=lambda r: (rank[r["kind"]], r["id"])):
        steps.append(Step(r["id"], r["kind"]))
    return steps
