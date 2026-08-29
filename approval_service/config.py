"""Environment-injected configuration, matching agent/config.py's own
convention exactly -- every environment difference via env vars, never a
rebuilt image (CLAUDE.md's contracts-not-couplings rule).

Contracts-STOP artifact (ADR-025).
"""

import os


def _env(name, default=None):
    return os.environ.get(name, default)


# Persistence (SRS-APR-DATA-01) -- SQLite on a PVC; the storage module's
# own interface stays narrow enough that
# swapping the backing store later doesn't touch the API layer.
APPROVAL_DB_PATH = _env("APPROVAL_DB_PATH", "./state/approval/approvals.db")

# SRS-APR-F-03 -- expiry, environment configuration, never hardcoded.
APPROVAL_TIMEOUT_SECONDS = int(_env("APPROVAL_TIMEOUT_SECONDS", "3600"))

# Agent -> approval-service auth. AUTH_MODE=none lets D1 be built, tested,
# and demoed before D2's real IdP exists (mirrors AGENT_MODEL_MODE's own
# fake/live toggle convention). Owner-added binding requirement (plan
# approval): once D2 lands, demo-prod's rendered config must assert
# AUTH_MODE=oidc mechanically (tools/check_config_contract.py or an
# equivalent manifest check) -- this switch is a security-relevant
# downgrade, treated like AUTO_APPROVE_IN_DEV, never left to convention.
AUTH_MODE = _env("AUTH_MODE", "none")  # none | oidc

# SRS-APR-SEC-02/03 -- populated once D2 delivers a real IdP; read but
# unused while AUTH_MODE=none.
OIDC_ISSUER_URL = _env("OIDC_ISSUER_URL")
OIDC_AUDIENCE = _env("OIDC_AUDIENCE")
APPROVER_ROLE_CLAIM = _env("APPROVER_ROLE_CLAIM", "roles")
APPROVER_ROLE_VALUE = _env("APPROVER_ROLE_VALUE", "approval-approver")

APPROVAL_PORT = int(_env("APPROVAL_PORT", "8082"))

# ADR-006: mirrors agent/config.py's identical OTEL_* pair.
OTEL_EXPORTER_OTLP_ENDPOINT = _env("OTEL_EXPORTER_OTLP_ENDPOINT")
OTEL_SERVICE_NAME = _env("OTEL_SERVICE_NAME", "golden-path-agent-approval")
