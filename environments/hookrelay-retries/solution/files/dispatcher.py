"""Dispatch due deliveries from the outbox, with retries and dead-lettering
(docs/RETRIES.md, HR-212)."""

import logging
from dataclasses import dataclass

from . import transport
from .outbox import Outbox
from .retry import DEFAULT_MAX_ATTEMPTS, backoff_delay

log = logging.getLogger("hookrelay.dispatch")


@dataclass
class DispatchStats:
    delivered: int = 0
    retried: int = 0
    dead: int = 0

    def as_dict(self):
        return {"delivered": self.delivered, "retried": self.retried, "dead": self.dead}


class Dispatcher:
    def __init__(self, outbox: Outbox, secret: str, *, send=transport.post, timeout: float = 10.0,
                 max_attempts: int = DEFAULT_MAX_ATTEMPTS):
        self.outbox = outbox
        self.secret = secret
        self.send = send
        self.timeout = timeout
        self.max_attempts = max_attempts

    def run_once(self, limit: int = 100) -> DispatchStats:
        stats = DispatchStats()
        for row in self.outbox.due(limit):
            result = self.send(row["endpoint"], row["body"], self.secret,
                               event_id=row["event_id"], timeout=self.timeout)
            attempts = row["attempts"] + 1
            if result.outcome == "delivered":
                self.outbox.update(row["id"], status="delivered", attempts=attempts, last_error="")
                stats.delivered += 1
            elif result.outcome == "retryable" and attempts < self.max_attempts:
                delay = backoff_delay(row["event_id"], attempts, result.retry_after)
                self.outbox.update(row["id"], attempts=attempts, last_error=result.error,
                                   next_attempt_at=self.outbox.clock() + delay)
                stats.retried += 1
            else:
                kind = "permanent" if result.outcome == "permanent" else "max attempts"
                self.outbox.dead_letter(row, attempts, f"{kind}: {result.error}")
                stats.dead += 1
                log.warning("delivery %s to %s dead-lettered: %s", row["id"], row["endpoint"],
                            result.error)
        return stats
