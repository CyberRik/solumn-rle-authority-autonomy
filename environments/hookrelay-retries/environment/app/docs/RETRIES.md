# HR-212: retries with backoff and a dead-letter queue

Status: agreed. Today every non-2xx attempt marks a delivery `failed` for good,
so a receiver that blips for a minute loses events. This replaces that.

## Behaviour

Outcomes come from `transport.classify` / `transport.post` as today:
`delivered`, `retryable`, `permanent`.

* **delivered** -> status `delivered` (unchanged).
* **retryable** -> the delivery stays `pending`, `attempts` is incremented and
  `next_attempt_at = now + backoff_delay(event_id, attempts, retry_after)`.
  Once a delivery has made `max_attempts` attempts (default **8**) and the last
  one was still retryable, it is dead-lettered instead.
* **permanent** -> dead-lettered immediately.

Dead-lettering sets status `dead`, records `last_error`, and appends a row to
the `dead_letters` table: `(delivery_id, event_id, endpoint, attempts, reason, at)`
where `reason` is `"permanent: <error>"` or `"max attempts: <error>"`.
The old `failed` status is no longer produced.

## Backoff

`hookrelay.retry.backoff_delay(event_id: str, attempt: int, retry_after: int | None = None) -> float`

`attempt` is the number of attempts made so far (1 after the first failure).

    base   = min(30 * 2 ** (attempt - 1), 3600)                 # seconds
    h      = int(sha256(f"{event_id}:{attempt}".encode()).hexdigest()[:8], 16)
    factor = 0.9 + 0.2 * h / 0xFFFFFFFF                          # deterministic +-10% jitter
    delay  = base * factor
    if retry_after is not None: delay = max(delay, retry_after)  # honour Retry-After
    return min(delay, 3600)

## API

* `Dispatcher(outbox, secret, *, send=transport.post, timeout=10.0, max_attempts=8)`
* `Dispatcher.run_once(limit=100)` returns stats whose `as_dict()` is
  `{"delivered": n, "retried": n, "dead": n}`.
* `Outbox.dead_letters()` -> list of dead-letter rows (oldest first), each with
  at least `delivery_id, event_id, endpoint, attempts, reason, at`.
* `Outbox.replay(delivery_id)` -> puts a dead delivery back to `pending` with
  `attempts = 0`, due now, and returns True; returns False if the delivery is
  not dead.
* CLI: `python -m hookrelay dlq` lists dead letters, `python -m hookrelay replay ID`.

## CI

As always, `scripts/ci.sh` must pass (tests + the coverage gate).
