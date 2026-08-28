"""OpenTelemetry tracing for approval_service (ADR-006). Mirrors
agent/telemetry.py's init/tracer pattern exactly -- same safe-no-op
behavior when the endpoint is unset, same OTLP/HTTP exporter, same
explicit /v1/traces suffix (see agent/telemetry.py for why the suffix
must be explicit).
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
    traces_endpoint = f"{config.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces"
    provider = TracerProvider(resource=Resource.create({"service.name": config.OTEL_SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_endpoint)))
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer():
    return trace.get_tracer(config.OTEL_SERVICE_NAME)


def record_transition_span(event: str, record: dict, span=None) -> None:
    """Phase D4's own attribute-correlation mechanism (the plan doc's D4
    section, adopted over real trace-context propagation across the async
    approval gap): session.id/proposal.id, the same attribute names
    agent/telemetry.py's own record_invocation_span uses -- a query joins
    across both services by those two values alone, not by trace id
    (each process's own span tree is independent; nothing here tries to
    thread one W3C trace context across the human-latency gap).

    `span` defaults to the current span (production use, matching
    agent/telemetry.py's own record_invocation_span); tests pass a fake
    span object to assert on set_attribute calls without a real OTel SDK
    span in play (the API's own default no-op span has no readable
    `.attributes` to assert against)."""
    if span is None:
        span = trace.get_current_span()
    span.set_attribute("proposal.id", record.get("proposal_id") or "")
    span.set_attribute("session.id", record.get("originating_session_id") or "")
    span.set_attribute("request.id", record.get("originating_request_id") or "")
    span.set_attribute("approval.event", event)
    span.set_attribute("approval.state", record.get("state") or "")
    span.set_attribute("approval.action_type", record.get("action_type") or "")
    span.set_attribute("approval.decided_by", record.get("decided_by") or "")
