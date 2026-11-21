"""Runtime settings, from the environment with defaults.

    HOOKRELAY_DB            outbox database        (/app/var/outbox.db)
    HOOKRELAY_SECRET_FILE   signing key file       (/app/var/signing.key)
    HOOKRELAY_TIMEOUT       per-attempt seconds    (10)
    HOOKRELAY_BATCH         deliveries per run     (100)
"""

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    db: str
    secret_file: Path
    timeout: float
    batch: int

    def secret(self) -> str:
        try:
            key = self.secret_file.read_text().strip()
        except OSError as exc:
            raise ConfigError(f"cannot read signing key {self.secret_file}: {exc}") from exc
        if not key:
            raise ConfigError(f"signing key {self.secret_file} is empty")
        return key


def _number(env, name, default, kind):
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = kind(raw)
    except ValueError:
        raise ConfigError(f"{name}={raw!r} is not a valid {kind.__name__}") from None
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def load(env=None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        db=env.get("HOOKRELAY_DB", "/app/var/outbox.db"),
        secret_file=Path(env.get("HOOKRELAY_SECRET_FILE", "/app/var/signing.key")),
        timeout=_number(env, "HOOKRELAY_TIMEOUT", 10.0, float),
        batch=_number(env, "HOOKRELAY_BATCH", 100, int),
    )
