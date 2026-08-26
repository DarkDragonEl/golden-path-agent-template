# `approval_service/`

Source for the shared human-approval gate (`api.py`, `auth.py`,
`config.py`, `schemas.py`, `store.py`, `telemetry.py`) — the enforcement
point for this project's defining objective, human approval on every
write. A Platform Foundation component (`DECISIONS.md` `DEC-098`), not
bundled per agent instance: one running instance serves every Agent
Template instantiation.

**Consumed by**: `Containerfile.approval` (builds its own independent
image), `deploy/kustomize/base/deployment-approval.yaml` (deploys it),
the agent (`agent/approval_client.py` submits proposals and polls
decisions), and a human approver (the approver UI served from
`agent/static/`, or `POST /proposals/{id}/decision` directly).

See the [documentation hub](../docs/README.md),
[`docs/security-identity.md`](../docs/security-identity.md) for the
approval control-flow contract,
[`docs/access-and-credentials.md`](../docs/access-and-credentials.md)
for who the demo approver account is, and
[`agent/README.md`](../agent/README.md) for its one caller.
