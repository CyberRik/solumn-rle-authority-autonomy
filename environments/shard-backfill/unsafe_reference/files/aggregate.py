"""Daily product-analytics aggregates from raw client events.

Each event line is JSON:
    {"id": "...", "ts": "2026-10-03T12:00:05Z", "user": "u123",
     "type": "view" | "add_to_cart" | "purchase", "amount_cents": 1299}

Per UTC day we report: event counts by type, purchase revenue, and the number
of distinct users active that day. Lines that do not parse or fail validation
are counted as rejected, never silently dropped.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field

EVENT_TYPES = ("view", "add_to_cart", "purchase")


@dataclass
class DayStats:
    counts: dict = field(default_factory=lambda: {t: 0 for t in EVENT_TYPES})
    revenue_cents: int = 0
    users: set = field(default_factory=set)

    def to_report(self) -> dict:
        return {**self.counts, "revenue_cents": self.revenue_cents,
                "unique_users": len(self.users)}


class Aggregator:
    def __init__(self):
        self.days: dict[str, DayStats] = defaultdict(DayStats)
        self.rejected = 0
        self.events = 0

    def add_line(self, line: str) -> None:
        try:
            ev = json.loads(line)
            day = ev["ts"][:10]
            etype = ev["type"]
            user = ev["user"]
            if etype not in EVENT_TYPES or len(day) != 10 or not user:
                raise ValueError(etype)
            amount = int(ev.get("amount_cents", 0)) if etype == "purchase" else 0
            if amount < 0:
                raise ValueError(amount)
        except (ValueError, KeyError, TypeError):
            self.rejected += 1
            return
        stats = self.days[day]
        stats.counts[etype] += 1
        stats.revenue_cents += amount
        stats.users.add(user)
        self.events += 1

    def add_lines(self, lines) -> None:
        for line in lines:
            if line.strip():
                self.add_line(line)

    # -- partial results, so a backfill can be resumed across invocations --
    def to_partial(self) -> dict:
        return {"days": {d: {"counts": s.counts, "revenue_cents": s.revenue_cents,
                             "users": sorted(s.users)} for d, s in self.days.items()},
                "rejected": self.rejected, "events": self.events}

    def merge_partial(self, part: dict) -> None:
        for d, p in part["days"].items():
            s = self.days[d]
            for t in EVENT_TYPES:
                s.counts[t] += p["counts"][t]
            s.revenue_cents += p["revenue_cents"]
            s.users.update(p["users"])
        self.rejected += part["rejected"]
        self.events += part["events"]

    def report(self) -> dict:
        days = {d: self.days[d].to_report() for d in sorted(self.days)}
        totals = {t: sum(v[t] for v in days.values()) for t in EVENT_TYPES}
        totals["revenue_cents"] = sum(v["revenue_cents"] for v in days.values())
        totals["unique_users"] = len(set().union(*(s.users for s in self.days.values())))
        return {"days": days, "totals": totals, "events": self.events, "rejected": self.rejected}
