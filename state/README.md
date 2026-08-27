# `state/`

Local runtime state for a laptop dev stack (`make up`/`make up-offline`)
or a single-replica live deployment — gitignored (`state/*`, this file
excepted), never committed.

**`state/approval/`** — `approval_service`'s SQLite database
(`APPROVAL_DB_PATH`, default `./state/approval/approvals.db`,
`approval_service/config.py`): the proposal store the approval flow
reads/writes. Deleting it resets all pending/decided proposals.

**`AGENT_STATE_DIR`** (`agent/config.py`, default `./state`) is defined
but not yet consumed by any code path — reserved, not currently used.

**Consumed by**: `approval_service` (the SQLite file above) and, when
deployed, the `state-approval` PVC (`deploy/kustomize/base/
pvc-approval.yaml`) that backs the same path in-cluster.
