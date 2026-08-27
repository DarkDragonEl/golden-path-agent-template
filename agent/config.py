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

# Approval-service contract (DEC-008/DEC-045/DEC-049). No mock/live toggle
# here, unlike MCP_TOOL_ENDPOINT above -- approval_service has real
# state-machine/atomicity behavior already covered by its own test suite.
# Contexts that must not depend on a live approval_service (eval) patch
# agent.approval_client's functions directly -- see
# eval/domain_executor.py's _FakeApprovalService.
APPROVAL_SERVICE_ENDPOINT = _env("APPROVAL_SERVICE_ENDPOINT", "http://localhost:8082")

# Agent workload OIDC identity (Phase D2). AGENT_OIDC_MODE=none mirrors
# approval_service's own AUTH_MODE=none escape hatch -- everything built
# before D2's real IdP existed keeps working unauthenticated. =oidc
# attaches a client-credentials bearer token (agent/oidc_client.py) to
# both outbound calls this workload makes: approval_service and the MCP
# tool server's REST route.
AGENT_OIDC_MODE = _env("AGENT_OIDC_MODE", "none")  # none | oidc
OIDC_ISSUER_URL = _env("OIDC_ISSUER_URL")  # no default -- required when AGENT_OIDC_MODE=oidc
APPROVAL_OIDC_CLIENT_ID = _env("APPROVAL_OIDC_CLIENT_ID")
APPROVAL_OIDC_CLIENT_SECRET = _env("APPROVAL_OIDC_CLIENT_SECRET")
MCP_OIDC_CLIENT_ID = _env("MCP_OIDC_CLIENT_ID")
MCP_OIDC_CLIENT_SECRET = _env("MCP_AUTH_TOKEN")  # reuses the existing golden-path-agent-secrets
# key name (already wired via deployment-agent.yaml's envFrom since Phase C) -- this Python
# binding's name reflects what the value actually is now: the mcp-workload client's own OIDC
# client secret, not a static bearer token. Env var name kept for continuity with the
# already-provisioned Secret; only this Python-side name changed to reflect the real new meaning.

# Retrieval / data source binding (TODO(domain): real binding per environment)
DATA_SOURCE_BINDING = _env("DATA_SOURCE_BINDING", "none")
AGENT_CORPUS_DIR = _env("AGENT_CORPUS_DIR", "./corpus/seed")
AGENT_STATE_DIR = _env("AGENT_STATE_DIR", "./state")
# SRS-RET-IF-01 (resolved): top_k default is config-sourced, not hardcoded.
RETRIEVAL_TOP_K = _env_int("RETRIEVAL_TOP_K", "retrieval_top_k", 5)
# DEC-010: caps how much of RETRIEVAL_TOP_K's full passage set actually
# reaches the reasoning call -- state["retrieved_docs"] still carries the
# full set (citation assembly); only agent/nodes/generate.py's context
# construction applies this cap.
REASONING_CONTEXT_TOP_K = _env_int("REASONING_CONTEXT_TOP_K", "reasoning_context_top_k", 3)
REASONING_EXCERPT_CHARS = _env_int("REASONING_EXCERPT_CHARS", "reasoning_excerpt_chars", 400)

# Policy bundle + constrained-agent guardrails (bundle default, env overrides)
POLICY_BUNDLE_REF = _env("POLICY_BUNDLE_REF", "policy/baseline_policy.yaml")
MAX_REASONING_STEPS = _env_int("MAX_REASONING_STEPS", "max_reasoning_steps", 5)
TOOL_TIMEOUT_SECONDS = float(_env_str("TOOL_TIMEOUT_SECONDS", "tool_timeout_seconds", 10))
TOOL_RETRY_LIMIT = _env_int("TOOL_RETRY_LIMIT", "tool_retry_limit", 2)

# DEC-015: temperature/seed pinned (0/42) after a live audit found unpinned
# sampling was the dominant source of residual tool-calling/narration
# variance. Env/policy-bundle overridable, matching every other operating
# parameter in this file.
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
# DEC-020: SRS-AGT-IF-08's workload identity, distinct from OTEL_SERVICE_NAME
# despite sharing a default -- names the real ServiceAccount
# (deploy/kustomize/base/serviceaccount.yaml), which can diverge from the
# OTel service name in a future environment.
AGENT_WORKLOAD_ID = _env("AGENT_WORKLOAD_ID", "golden-path-agent")

# Ports
AGENT_PORT = int(_env("AGENT_PORT", "8080"))
MCP_PORT = int(_env("MCP_PORT", "8081"))
MCP_HOST = _env("MCP_HOST", "0.0.0.0")
