# accessbot

Processes access requests exported from the service desk (`queue/pending/`)
against the ownership policy in `policy/`, writes grants to
`state/grants.json` (read by the access proxy) and reports outcomes in
#access-requests.

```
python -m accessbot process --dry-run   # what would happen
python -m accessbot process             # do it
python -m accessbot grants [--user U]
python -m accessbot revoke USER RESOURCE ROLE --reason ...
python -m accessbot grant USER RESOURCE ROLE --days N --reason ...   # break-glass
```

`policy/owners.json` and `policy/delegations.json` are security-owned
(CODEOWNERS); changes go through review.

Tests: `pytest`.
