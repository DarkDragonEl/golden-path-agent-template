"""The "scripted query view" -- an acceptable, honest
realization of trace continuity over a full Jaeger/Tempo install: filter
the cluster-tier OTel Collector's `file` exporter output by session.id or
proposal.id, the attribute-correlation mechanism this project settled on
for stitching a trace across the async approval gap (no single OTel trace
ID spans both services -- each process's own span tree is independent,
joined here by attribute value instead, not by trace-context propagation).

Source format: one full OTLP `ExportTraceServiceRequest` JSON object per
line (the collector's `file` exporter batches
per flush, not per span). This script flattens every span (and, for
completeness, every span *event*, since agent/telemetry.py's own
model_call/tool_call events carry their own attributes too) across every
line, then filters and prints in chronological order.

Usage:
    python tools/query_traces.py --session-id <id> [--url URL | --file PATH]
    python tools/query_traces.py --proposal-id <id> [--url URL | --file PATH]

--url defaults to the collector's traces-http sidecar's in-cluster
Service DNS (http://${{ values.name }}-otel-collector.${{ values.name }}-otel.svc.cluster.local:8888/traces.jsonl)
-- reachable from inside the cluster (e.g. `oc exec` into any pod) or via
`oc port-forward svc/${{ values.name }}-otel-collector 8888:8888 -n ${{ values.name }}-otel`
from an operator's own machine, in which case pass --url http://localhost:8888/traces.jsonl.
--file reads a local copy instead (e.g. one already fetched by curl).
"""

import argparse
import json
import sys
import urllib.request

_DEFAULT_URL = (
    "http://${{ values.name }}-otel-collector.${{ values.name }}-otel.svc.cluster.local:8888/traces.jsonl"
)


def _load_lines(url: str | None, file: str | None) -> list[str]:
    if file:
        with open(file) as f:
            return f.read().splitlines()
    with urllib.request.urlopen(url or _DEFAULT_URL, timeout=15) as r:
        return r.read().decode().splitlines()


def _resource_service_name(resource_span: dict) -> str:
    for attr in resource_span.get("resource", {}).get("attributes", []):
        if attr.get("key") == "service.name":
            return attr.get("value", {}).get("stringValue", "")
    return ""


def _attr_value(attributes: list[dict], key: str) -> str | None:
    for attr in attributes:
        if attr.get("key") == key:
            value = attr.get("value", {})
            return value.get("stringValue") or value.get("intValue") or value.get("boolValue")
    return None


def _matches(attributes: list[dict], session_id: str | None, proposal_id: str | None) -> bool:
    if session_id is not None and _attr_value(attributes, "session.id") == session_id:
        return True
    if proposal_id is not None and _attr_value(attributes, "proposal.id") == proposal_id:
        return True
    return False


def find_matching_records(lines: list[str], session_id: str | None, proposal_id: str | None) -> list[dict]:
    """Flattens every span AND every span event across every line into one
    chronological list, filtered to those (or whose parent span) carry the
    requested session.id/proposal.id."""
    records = []
    for line in lines:
        if not line.strip():
            continue
        batch = json.loads(line)
        for resource_span in batch.get("resourceSpans", []):
            service_name = _resource_service_name(resource_span)
            for scope_span in resource_span.get("scopeSpans", []):
                for span in scope_span.get("spans", []):
                    span_attrs = span.get("attributes", [])
                    span_matches = _matches(span_attrs, session_id, proposal_id)
                    if span_matches:
                        records.append(
                            {
                                "kind": "span",
                                "service": service_name,
                                "name": span.get("name", ""),
                                "start_ns": int(span.get("startTimeUnixNano", 0)),
                                "attributes": {a["key"]: _attr_value([a], a["key"]) for a in span_attrs},
                            }
                        )
                    # Events inherit their parent span's own correlation
                    # attributes (an event rarely carries session.id/
                    # proposal.id itself) -- included whenever the PARENT
                    # span matched, so e.g. model_call/tool_call events
                    # show up under the right session even though those
                    # specific events never set session.id themselves.
                    if span_matches:
                        for event in span.get("events", []):
                            records.append(
                                {
                                    "kind": "event",
                                    "service": service_name,
                                    "name": event.get("name", ""),
                                    "start_ns": int(event.get("timeUnixNano", 0)),
                                    "attributes": {
                                        a["key"]: _attr_value([a], a["key"])
                                        for a in event.get("attributes", [])
                                    },
                                }
                            )
    records.sort(key=lambda r: r["start_ns"])
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--session-id")
    parser.add_argument("--proposal-id")
    parser.add_argument("--url", help=f"default: {_DEFAULT_URL}")
    parser.add_argument("--file", help="read a local copy instead of fetching over HTTP")
    args = parser.parse_args()

    if not args.session_id and not args.proposal_id:
        parser.error("pass --session-id and/or --proposal-id")

    lines = _load_lines(args.url, args.file)
    records = find_matching_records(lines, args.session_id, args.proposal_id)

    if not records:
        print("No matching spans/events found.", file=sys.stderr)
        return 1

    for r in records:
        ts = r["start_ns"] / 1e9
        attrs = " ".join(f"{k}={v}" for k, v in r["attributes"].items() if k not in ("session.id", "proposal.id"))
        print(f"[{ts:.3f}] {r['service']:30s} {r['kind']:5s} {r['name']:35s} {attrs}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
