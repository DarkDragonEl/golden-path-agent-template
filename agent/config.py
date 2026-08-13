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

# Model contract
MODEL_API_BASE_URL = _env("MODEL_API_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = _env("MODEL_NAME", "placeholder-model")
MODEL_API_KEY = _env("MODEL_API_KEY", "not-needed")
AGENT_MODEL_MODE = _env("AGENT_MODEL_MODE", "live")  # live | fake

# MCP tool contract
MCP_TOOL_ENDPOINT = _env("MCP_TOOL_ENDPOINT", "http://localhost:8081")
MCP_MODE = _env("MCP_MODE", "mock")  # mock | live

# Retrieval / data source binding (TODO(domain): real binding per environment)
DATA_SOURCE_BINDING = _env("DATA_SOURCE_BINDING", "none")
AGENT_CORPUS_DIR = _env("AGENT_CORPUS_DIR", "./corpus/seed")
AGENT_STATE_DIR = _env("AGENT_STATE_DIR", "./state")

# Policy bundle + constrained-agent guardrails (bundle default, env overrides)
POLICY_BUNDLE_REF = _env("POLICY_BUNDLE_REF", "policy/baseline_policy.yaml")
MAX_REASONING_STEPS = _env_int("MAX_REASONING_STEPS", "max_reasoning_steps", 5)
TOOL_TIMEOUT_SECONDS = float(_env_str("TOOL_TIMEOUT_SECONDS", "tool_timeout_seconds", 10))
TOOL_RETRY_LIMIT = _env_int("TOOL_RETRY_LIMIT", "tool_retry_limit", 2)
APPROVAL_MODE = _env_str("APPROVAL_MODE", "approval_mode", "required")  # required | auto
AUTO_APPROVE_IN_DEV = _env("AUTO_APPROVE_IN_DEV", "false").lower() == "true"

# Telemetry
OTEL_EXPORTER_OTLP_ENDPOINT = _env("OTEL_EXPORTER_OTLP_ENDPOINT")
OTEL_SERVICE_NAME = _env("OTEL_SERVICE_NAME", "golden-path-agent")

# Ports
AGENT_PORT = int(_env("AGENT_PORT", "8080"))
MCP_PORT = int(_env("MCP_PORT", "8081"))
MCP_HOST = _env("MCP_HOST", "0.0.0.0")
