"""Environment-injected configuration.

Every environment difference (local, ephemeral-test, staging, pilot-prod)
must be expressed here via env vars / the policy bundle — never via a
rebuilt image. See deploy/kustomize/base/configmap.yaml for the concrete
per-environment values.
"""

import os
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _env(name, default=None):
    return os.environ.get(name, default)


def _load_policy_bundle() -> dict:
    ref = _env("POLICY_BUNDLE_REF", "policy/baseline_policy.yaml")
    path = Path(ref)
    if not path.is_absolute():
        path = _REPO_ROOT / ref
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _load_approval_rules() -> dict:
    ref = _env("APPROVAL_RULES_REF", "policy/approval_rules.yaml")
    path = Path(ref)
    if not path.is_absolute():
        path = _REPO_ROOT / ref
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _env_int(name, bundle_key, hard_default):
    raw = os.environ.get(name)
    if raw is not None:
        return int(raw)
    return int(_POLICY_BUNDLE.get(bundle_key, hard_default))


def _env_str(name, bundle_key, hard_default):
    raw = os.environ.get(name)
    if raw is not None:
        return raw
    return str(_POLICY_BUNDLE.get(bundle_key, hard_default))


_POLICY_BUNDLE = _load_policy_bundle()
_APPROVAL_RULES_BUNDLE = _load_approval_rules()

# Model contract
MODEL_API_BASE_URL = _env("MODEL_API_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = _env("MODEL_NAME", "placeholder-model")
MODEL_API_KEY = _env("MODEL_API_KEY", "not-needed")
AGENT_MODEL_MODE = _env("AGENT_MODEL_MODE", "live")  # live | fake

# Fallback route (SysR-P-F-12, DECISIONS.md DEC-009). Unset => no fallback
# configured; RoutedModelClient re-raises on primary failure instead of
# retrying. Same API key as primary -- both routes are the same MaaS today
# (DEC-009); a separate key isn't needed until that's no longer true.
MODEL_FALLBACK_API_BASE_URL = _env("MODEL_FALLBACK_API_BASE_URL")
MODEL_FALLBACK_NAME = _env("MODEL_FALLBACK_NAME")

# MCP tool contract
MCP_TOOL_ENDPOINT = _env("MCP_TOOL_ENDPOINT", "http://localhost:8081")
MCP_MODE = _env("MCP_MODE", "mock")  # mock | live

# Approval-service contract (Phase D, DECISIONS.md DEC-008/DEC-045/DEC-049).
# No mock/live toggle here, unlike MCP_TOOL_ENDPOINT above -- unlike the
# mock ITSM tool (simple synchronous functions with an obvious in-process
# equivalent), approval_service has real state-machine/atomicity behavior
# already covered by its own test suite (tests/test_approval_service.py);
# duplicating that here would risk drifting out of sync with the real
# service. Contexts that must not depend on a live approval_service (the
# eval harness) patch agent.approval_client's functions directly instead
# -- see eval/domain_executor.py's _FakeApprovalService.
APPROVAL_SERVICE_ENDPOINT = _env("APPROVAL_SERVICE_ENDPOINT", "http://localhost:8082")

# Retrieval / data source binding (TODO(domain): real binding per environment)
DATA_SOURCE_BINDING = _env("DATA_SOURCE_BINDING", "none")
AGENT_CORPUS_DIR = _env("AGENT_CORPUS_DIR", "./corpus/seed")
AGENT_STATE_DIR = _env("AGENT_STATE_DIR", "./state")
# SRS-RET-IF-01 (resolved): top_k default is config-sourced, not hardcoded.
RETRIEVAL_TOP_K = _env_int("RETRIEVAL_TOP_K", "retrieval_top_k", 5)
# Structural mitigation for a Phase B4 live-testing finding: draft_request
# and tool_selection failed their thresholds decisively (measured, not
# assumed -- reports/feature-phase-b-golden-path.md) when the full
# RETRIEVAL_TOP_K passages were injected into the reasoning call verbatim
# -- a detailed procedure document in context reliably out-competed the
# tool schemas for the model's attention. state["retrieved_docs"] still
# carries the full RETRIEVAL_TOP_K set (citation assembly, future
# consumers); only agent/nodes/generate.py's own context construction caps
# how much of it actually reaches the model (DEC-013 candidate: this
# capping is a secondary mitigation now that agent/nodes/decide.py never
# sees retrieved context at all -- see DECISIONS.md DEC-012/DEC-013).
REASONING_CONTEXT_TOP_K = _env_int("REASONING_CONTEXT_TOP_K", "reasoning_context_top_k", 3)
REASONING_EXCERPT_CHARS = _env_int("REASONING_EXCERPT_CHARS", "reasoning_excerpt_chars", 400)

# Policy bundle + constrained-agent guardrails (bundle default, env overrides)
POLICY_BUNDLE_REF = _env("POLICY_BUNDLE_REF", "policy/baseline_policy.yaml")
MAX_REASONING_STEPS = _env_int("MAX_REASONING_STEPS", "max_reasoning_steps", 5)
TOOL_TIMEOUT_SECONDS = float(_env_str("TOOL_TIMEOUT_SECONDS", "tool_timeout_seconds", 10))
TOOL_RETRY_LIMIT = _env_int("TOOL_RETRY_LIMIT", "tool_retry_limit", 2)

# R3 remedy (DEC-015): neither temperature nor seed was pinned before this --
# the model client relied entirely on the endpoint's own default sampling.
# A live audit found this was the dominant source of the residual pass-to-
# pass tool-calling/narration variance (DEC-012/DEC-013/DEC-014's noise
# categories): the same decide-shaped call, unpinned, alternated between a
# real tool_calls response and prose narration across repeated calls;
# pinned (temperature=0, seed=42), 3/3 repeated calls returned an identical
# tool_calls response. Both values are env/policy-bundle overridable per
# this file's own convention -- not because a different temperature is
# expected to be needed, but because every other operating parameter here
# already is, and pinning determinism should not be the one hardcoded
# exception.
MODEL_TEMPERATURE = _env_int("MODEL_TEMPERATURE", "model_temperature", 0)
MODEL_SEED = _env_int("MODEL_SEED", "model_seed", 42)
APPROVAL_MODE = _env_str("APPROVAL_MODE", "approval_mode", "required")  # required | auto
AUTO_APPROVE_IN_DEV = _env("AUTO_APPROVE_IN_DEV", "false").lower() == "true"

# Tool-name classification taxonomy (SRS-AGT-SEC-03 fail-closed default —
# see policy/approval_rules.yaml). Consumed by agent/policy.py::classify_action.
APPROVAL_RULES_REF = _env("APPROVAL_RULES_REF", "policy/approval_rules.yaml")
TOOL_CLASSIFICATION: dict = {
    r["tool_name"]: r["classification"] for r in _APPROVAL_RULES_BUNDLE.get("rules", [])
}
DEFAULT_TOOL_CLASSIFICATION = _APPROVAL_RULES_BUNDLE.get("default_classification", "write")

# Telemetry
OTEL_EXPORTER_OTLP_ENDPOINT = _env("OTEL_EXPORTER_OTLP_ENDPOINT")
OTEL_SERVICE_NAME = _env("OTEL_SERVICE_NAME", "golden-path-agent")
# R4/DEC-020: SRS-AGT-IF-08 "the agent's workload identity", distinct from
# OTEL_SERVICE_NAME (an OTel resource-attribute convention) even though
# they share a default -- this names the actual runtime identity
# (deploy/kustomize/base/serviceaccount.yaml's ServiceAccount), which can
# diverge from the OTel service name in a future environment.
AGENT_WORKLOAD_ID = _env("AGENT_WORKLOAD_ID", "golden-path-agent")

# Ports
AGENT_PORT = int(_env("AGENT_PORT", "8080"))
MCP_PORT = int(_env("MCP_PORT", "8081"))
MCP_HOST = _env("MCP_HOST", "0.0.0.0")
