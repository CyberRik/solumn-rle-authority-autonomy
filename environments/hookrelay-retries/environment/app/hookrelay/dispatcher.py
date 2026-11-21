"""Dispatch due deliveries from the outbox.

Today a delivery gets exactly one attempt: anything other than a 2xx marks it
failed. See docs/RETRIES.md for the retry / dead-letter design (HR-212).
"""

import logging
from dataclasses import dataclass

from . import transport
from .outbox import Outbox

log = logging.getLogger("hookrelay.dispatch")


@dataclass
class DispatchStats:
    delivered: int = 0
    failed: int = 0

    def as_dict(self):
        return {"delivered": self.delivered, "failed": self.failed}


class Dispatcher:
    def __init__(self, outbox: Outbox, secret: str, *, send=transport.post, timeout: float = 10.0):
        self.outbox = outbox
        self.secret = secret
        self.send = send
        self.timeout = timeout

    def run_once(self, limit: int = 100) -> DispatchStats:
        stats = DispatchStats()
        for row in self.outbox.due(limit):
            result = self.send(row["endpoint"], row["body"], self.secret,
                               event_id=row["event_id"], timeout=self.timeout)
            attempts = row["attempts"] + 1
            if result.outcome == "delivered":
                self.outbox.update(row["id"], status="delivered", attempts=attempts, last_error="")
                stats.delivered += 1
            else:
                self.outbox.update(row["id"], status="failed", attempts=attempts,
                                   last_error=result.error)
                stats.failed += 1
                log.warning("delivery %s to %s failed: %s", row["id"], row["endpoint"], result.error)
        return stats
