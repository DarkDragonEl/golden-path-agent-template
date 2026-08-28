# ADR-014: Eval-Only Fault-Injection Fixture, Decoupled from the Real MCP Server

## Context
Domain eval cases need deterministic tool-failure scenarios (timeout/error)
to test agent behavior under tool failure. The real MCP server's mock ITSM
store has a `_simulate_error` hook, deliberately never exposed as a tool
parameter on the real call path — documented as categorically unreachable
from a real agent-constructed call. Once the MCP server became a genuinely
separate, network-deployed process, how to inject faults for eval without
weakening that guarantee needed a decision.

## Decision
Fault injection for domain eval moves to an in-process eval fixture in
`eval/` tooling — a thin mirror of the mock ITSM store's contract, driven
through a test-only MCP client stub — rather than adding a config-gated
fault-injection surface to the real, deployed MCP server or standing up a
second, purpose-built eval-only MCP server.

## Consequences
- The real MCP server's `_simulate_error` hook stays unexposed and
  unmodified; nothing about the deployed server's attack surface changes.
- Domain eval keeps full determinism but gives up real network-fault
  fidelity; the integration suite (`MCP_MODE=live` split-validation) must
  separately cover at least one genuine network-level fault case (e.g.
  killing or NetworkPolicy-blocking the MCP pod mid-run) and verify the
  agent's real timeout/error handling — this gap must not go uncovered.
- Because this is a template scaffolded to every future team, adopters must
  not add a config-gated fault surface to the real server as a shortcut —
  that would ship everywhere, guarded only by an environment flag,
  inconsistent with structurally-gated writes.
- A second, eval-only MCP server was rejected: domain-eval cases test agent
  behavior under tool failure, not server internals, so an in-process
  fixture is sufficient fidelity without the extra implementation to maintain.

## Supersedes / Superseded-by
None.

## Journal
DEC-105
