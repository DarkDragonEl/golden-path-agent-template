"""OpenTelemetry tracing. Safe to import/use even when OTEL_EXPORTER_OTLP_ENDPOINT
is unset — the OTel API always provides a working no-op tracer, so spans are
just discarded locally instead of erroring.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from . import config

_initialized = False


def init_telemetry() -> None:
    global _initialized
    if _initialized or not config.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": config.OTEL_SERVICE_NAME}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer():
    return trace.get_tracer(config.OTEL_SERVICE_NAME)


def record_invocation_span(state: dict) -> None:
    """Captures the proposal's required telemetry fields onto the current
    span: session id, user/workload identity, model/endpoint, retrieved doc
    ids, tool calls, policy/approval decisions.

    TODO(domain): token consumption isn't captured yet — FakeModelClient and
    most OpenAI-compatible backends don't report it uniformly; wire it once
    a real model endpoint is selected.
    """
    span = trace.get_current_span()
    span.set_attribute("session.id", state.get("session_id", ""))
    span.set_attribute("user.id", state.get("user_id", ""))
    span.set_attribute("model.name", config.MODEL_NAME)
    span.set_attribute("model.endpoint", config.MODEL_API_BASE_URL)
    # SysR-P-F-12 / SRS-AGT-IF-02: routing decision + reason code, set by
    # agent/nodes/decide.py and agent/nodes/generate.py on every call they
    # make (Phase B3; DEC-013 candidate split decide/generate into two
    # nodes -- these two scalars reflect the last call only; state["model_calls"]
    # is the per-call source of truth used by eval/domain_scorer.py's
    # DEC-009 compensating control).
    span.set_attribute("model.route", state.get("model_route") or "")
    span.set_attribute("model.route_reason_code", state.get("model_route_reason_code") or "")
    span.set_attribute(
        "retrieved_doc.ids", ",".join(d.get("doc_id", "") for d in state.get("retrieved_docs", []))
    )
    span.set_attribute("tool_calls.count", len(state.get("tool_calls", [])))
    span.set_attribute("approval.decision", str(state.get("approval_decision")))
    span.set_attribute("policy_bundle.ref", config.POLICY_BUNDLE_REF)
