# Security & identity

## Workload identity

`deploy/kustomize/base/serviceaccount.yaml` is the identity anchor every
Deployment runs under (`serviceAccountName: ${{ values.name }}` on both the
agent and MCP pods). Its OIDC/workload-identity federation annotation is
TODO(platform) — left empty in the base, meant to be added per environment
via an overlay patch once a real identity provider integration is chosen.

## Secrets

`deploy/kustomize/base/externalsecret.yaml` is a placeholder assuming the
External Secrets Operator (`external-secrets.io`) syncs `MODEL_API_KEY` and
`MCP_AUTH_TOKEN` from whatever enterprise secrets manager gets chosen. If a
different mechanism is used for the real engagement, replace this file's
`kind` entirely — don't force a different tool into this shape.

## Network boundary between agent and MCP

Even though both roles ship from the same container image,
`deploy/kustomize/base/networkpolicy.yaml` restricts ingress to the MCP
pod to only the agent pod's label selector. This is the "independent
security boundary" the architecture doc's one-image-two-roles design
relies on.

## The human-approval gate

This is the proposal's "human approval for every external write"
requirement, implemented as actual control flow, not documentation:

1. `agent/policy.py::classify_action()` inspects the tool call's `write`
   flag. `write: false` (or absent) → `"read"`, auto-completes.
   `write: true` → `"write"`, requires approval whenever
   `APPROVAL_MODE=required` (the default in every overlay).
2. `agent/nodes/tool_invoke.py` sets `pending_approval=True` for
   write-classified calls, and the graph — compiled with
   `interrupt_before=["human_approval"]` — actually stops before running
   the approval node.
3. Resuming requires an explicit `POST /approvals/{session_id}/resume`
   call with `{"decision": "approve"}` or `{"decision": "reject"}`.
   Rejection routes to the deterministic fallback, not to a retry.

Verified end-to-end against a running container (not just unit tests):
invoke with `write: true` returns `pending_approval: true` and no
`final_output`; resume with `approve` returns the completed result;
`eval/cases/EXAMPLE-002.yaml` encodes this exact sequence as a CI-gated
regression case.

`AUTO_APPROVE_IN_DEV` exists as a dev-only convenience (skips the pause
when no decision has been set) and must never be `true` in the staging or
pilot-prod overlay ConfigMaps — none of them set it.

## TODO(domain): the real consequential-action taxonomy

`classify_action()` today only has one signal: an explicit `write` flag on
the tool call arguments. Once real domain tools exist, replace this with
whatever taxonomy actually distinguishes safe reads from consequential
writes for those tools — `policy/approval_rules.yaml` is the intended
future home for that as declarative config instead of hardcoded logic.

## Not yet included (see the reuse-map artifact's gaps table)

No prompt-injection/PII/toxicity guard service is wired into this
scaffold. `eval/scorer.py` has a `semantic_judge` assertion type
plumbed but unused by the placeholder cases — a real security eval suite
(prompt-injection resistance, policy compliance) is domain content, not
infrastructure, and belongs in `eval/cases/` once a use case is chosen.
