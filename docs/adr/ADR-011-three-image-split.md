# ADR-011: Three-Image Split (Agent, MCP Tools, Approval)

## Context
A single Containerfile previously bundled `agent/`, `mcp_server/`, and
`approval_service/` into one image, with `entrypoint.sh` selecting a runtime
role from a positional argument. Once the approval service becomes a shared
Platform Foundation component serving multiple agent instances, and once
agent and tool code evolve independently, one shared image and one
case-statement dispatch no longer matches the deployment shape.

## Decision
The agent, MCP/tools, and approval service are each built as their own
independently-built, independently-promoted, independently-live OCI image,
with its own Containerfile, Tekton pipeline, and promotion path.
`CLAUDE.md`'s "one immutable artifact" rule is realized as one immutable
artifact per component, not one artifact for the whole system.

## Consequences
- Each component's image excludes the other components' code by construction
  (e.g. the agent image has no `mcp_server/server.py`); dev/CI configuration
  that assumes in-process fallback across components (`MCP_MODE=mock`'s
  `from . import server`) will crash-loop the split agent image and must not
  be used against it — `MCP_MODE=live` is required.
- Ephemeral testing overrides only the digest of the component under test;
  the other two render at their last-promoted digest ("test against what's
  deployed"), since builds now promote independently. Digest-editing and
  promotion-PR tooling must be scoped per image name and per-component
  branch name, or a shared edit/branch will collide across images.
- Adopters must not reintroduce a single shared image or positional-role
  dispatch once more than one Agent Template instance shares the approval
  service; doing so reverts to N inconsistent approval workflows.

## Supersedes / Superseded-by
Supersedes the single-Containerfile, positional-role-dispatch image
(`entrypoint.sh`'s case statement) and the single shared `golden-path-agent-ci`
pipeline.

## Journal
DEC-101
