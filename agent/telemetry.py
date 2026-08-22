"""OpenTelemetry tracing. Safe to import/use even when OTEL_EXPORTER_OTLP_ENDPOINT
is unset — the OTel API always provides a working no-op tracer, so spans are
just discarded locally instead of erroring.

R4/DEC-020 (plan-B6 closure): every attribute/event set here is read-only
with respect to model inputs -- this module only observes already-computed
state and already-on-disk prompt files; it never alters the system prompt,
user message, or `tools=` argument actually sent to the model. This is a
hard constraint, not a style preference (see HANDOFF.md's R0 forward
notes) -- changing that would make telemetry itself an undeclared
DEC-012-style instrument change.
"""

import hashlib
from pathlib import Path

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from . import config

_initialized = False

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _prompt_version(filename: str) -> str:
    """SRS-AGT-DATA-01: a short content hash, computed by reading the same
    on-disk prompt file the agent already loads to build its calls -- never
    embedded back into the prompt text itself (that would make prompt
    versioning trigger DEC-012's re-baseline rule every time telemetry
    changed). Out-of-band by construction: this hash reaches only the
    telemetry span, never a message sent to the model."""
    path = _PROMPTS_DIR / filename
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except FileNotFoundError:
        return "unknown"


# Computed once at import time -- both files are static repo content, not
# per-run state.
_DECIDE_PROMPT_VERSION = _prompt_version("decide_system_prompt.md")
_GENERATE_PROMPT_VERSION = _prompt_version("generate_system_prompt.md")


def init_telemetry() -> None:
    global _initialized
    if _initialized or not config.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    # The HTTP exporter only auto-appends the per-signal path (/v1/traces)
    # when it resolves OTEL_EXPORTER_OTLP_ENDPOINT itself; passing `endpoint`
    # explicitly (as here, since config.py already centralizes env reads)
    # makes it use the value verbatim -- confirmed live against the R4 dev
    # OTel Collector: the base URL alone 404'd ("Failed to export span
    # batch code: 404, reason: Not Found") until /v1/traces was appended.
    traces_endpoint = f"{config.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces"
    provider = TracerProvider(resource=Resource.create({"service.name": config.OTEL_SERVICE_NAME}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_endpoint))
    )
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer():
    return trace.get_tracer(config.OTEL_SERVICE_NAME)


def record_invocation_span(state: dict, request_id: str | None = None, span=None) -> None:
    """Captures SRS-AGT-IF-08's required telemetry fields onto a span:
    request/session identifiers, initiating user + agent workload identity,
    prompt-template version, retrieved doc ids, every model call's route
    and reason code (SysR-P-F-12/SRS-AGT-IF-02), every tool call and its
    arguments/policy classification, the approval outcome, and a reference
    to the final result.

    `span` defaults to the current span (production use); tests pass a
    fake span object to assert on `set_attribute`/`add_event` calls without
    a real OTel SDK span in play.
    """
    if span is None:
        span = trace.get_current_span()

    span.set_attribute("session.id", state.get("session_id", ""))
    span.set_attribute("request.id", request_id or "")
    span.set_attribute("user.id", state.get("user_id", ""))
    span.set_attribute("workload.id", config.AGENT_WORKLOAD_ID)
    span.set_attribute("model.name", config.MODEL_NAME)
    span.set_attribute("model.endpoint", config.MODEL_API_BASE_URL)
    span.set_attribute("prompt.decide_version", _DECIDE_PROMPT_VERSION)
    span.set_attribute("prompt.generate_version", _GENERATE_PROMPT_VERSION)

    # SysR-P-F-12 / SRS-AGT-IF-02: routing decision + reason code, for
    # EVERY model call this turn -- state["model_calls"] (DEC-013's
    # decide/generate split can make two calls per turn) is the source of
    # truth; one event per call, not the last-write-wins scalar fields
    # below, which stay only as a last-call convenience (matching
    # eval/domain_scorer.py's own DEC-009 compensating-control fix -- the
    # route-coverage gap this closes on the telemetry side).
    for call in state.get("model_calls", []):
        span.add_event(
            "model_call",
            attributes={
                "model_call.node": call.get("node", ""),
                "model_call.route": call.get("route", ""),
                "model_call.reason_code": call.get("reason_code", ""),
                "model_call.prompt_tokens": call.get("prompt_tokens") or -1,
                "model_call.completion_tokens": call.get("completion_tokens") or -1,
                "model_call.total_tokens": call.get("total_tokens") or -1,
                "model_call.response_model": call.get("response_model") or "",
            },
        )
    last_call = state.get("model_calls", [])[-1] if state.get("model_calls") else {}
    span.set_attribute("model.route", last_call.get("route") or state.get("model_route") or "")
    span.set_attribute(
        "model.route_reason_code", last_call.get("reason_code") or state.get("model_route_reason_code") or ""
    )

    span.set_attribute(
        "retrieved_doc.ids", ",".join(d.get("doc_id", "") for d in state.get("retrieved_docs", []))
    )

    # SRS-AGT-IF-04/F-06: every tool call, its policy classification (the
    # "every policy decision" half of SRS-AGT-IF-08 not covered by the
    # final approval.decision below), and its outcome -- one event per
    # call, mirroring the model_call events above.
    for tc in state.get("tool_calls", []):
        span.add_event(
            "tool_call",
            attributes={
                "tool_call.tool_name": tc.get("tool_name", ""),
                "tool_call.classification": tc.get("classification", ""),
                "tool_call.error": tc.get("error") or "",
            },
        )
    span.set_attribute("tool_calls.count", len(state.get("tool_calls", [])))

    span.set_attribute("approval.decision", str(state.get("approval_decision")))
    span.set_attribute("policy_bundle.ref", config.POLICY_BUNDLE_REF)

    # SRS-AGT-F-05/SysR-P-F-12: whatever escape-hatch reason (tool error,
    # model failure, approval not granted, step limit) this run hit, if any.
    span.set_attribute("fallback_reason", state.get("fallback_reason") or "")

    # "A reference to the final result" -- length + a short preview, not
    # the full text (span attributes aren't the place for potentially
    # large/sensitive response bodies; this is enough for a developer to
    # confirm a run produced a real answer).
    final_output = state.get("final_output") or ""
    span.set_attribute("final_output.length", len(final_output))
    span.set_attribute("final_output.preview", final_output[:200])
