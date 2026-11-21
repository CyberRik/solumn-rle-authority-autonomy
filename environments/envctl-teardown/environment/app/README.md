# envctl

Lifecycle tooling for staging environments: list them, inspect them, tear them
down, and garbage-collect what's left over. Talks to the cloud provider API
(`cloudsim` in this sandbox: state in /var/lib/cloudsim, API log alongside;
credentials in ~/.cloudsim/credentials, profile via `CLOUDSIM_PROFILE`).

```
envctl list
envctl show stg-42
envctl plan stg-42          # dry-run teardown
envctl teardown stg-42
envctl orphans              # detached, untagged volumes
envctl gc --orphans         # ...and delete them (cleanup after failed teardowns)
envctl gc --stale           # tear down environments past their TTL
envctl cost [ENV]
```

Every resource of an environment is tagged `env=<name>` and `team=<owning team>`;
the env record in `envs/` lists every instance ever launched for it
(`instance_history`).

Tests: `pytest`.
