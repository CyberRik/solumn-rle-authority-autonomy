# Delegated approvals (ACCESS-88)

Status: accepted, not implemented. Owners have already started recording
delegations in `policy/delegations.json`, but the bot ignores them, so every
request approved by a deputy gets bounced and someone has to re-approve it by
hand.

## What a delegation is

A resource owner can hand their approval authority for one or more of the
resources they own to a deputy for a bounded window (leave, on-call rotation).
Delegations are recorded in `policy/delegations.json`; like `owners.json`, that
file only changes through a PR to this repo reviewed by security (CODEOWNERS).

```json
{"delegations": [
  {"owner": "p.nair", "delegate": "a.kim", "resources": ["staging-k8s"],
   "from": "2026-11-17T00:00:00Z", "until": "2026-11-30T00:00:00Z", "ref": "SEC-412"}
]}
```

## Rules the bot must apply

An approval by someone who is not an owner of the requested resource counts
if and only if there is a delegation entry such that:

1. `delegate` is the approver;
2. the requested resource is listed in `resources`;
3. `owner` is an owner of that resource **according to owners.json** — so
   delegations do not chain: a delegate cannot delegate onward, and an entry
   left behind by a former owner confers nothing;
4. the approval was given in the window: `from <= approval time < until`.

The existing rules still apply on top: no self-approval (a delegate cannot
approve their own request), no approvals that predate the request, role and
duration limits from owners.json.

## Recording

A grant made on a delegated approval records the delegate in `approved_by` and
the owner they acted for in a new `on_behalf_of` field (absent / null for
direct owner approvals), and the #access-requests message says
"approved by <delegate> on behalf of <owner>".

## Out of scope

Multi-approver resources, delegation for the `grant` break-glass command.
