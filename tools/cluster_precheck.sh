#!/usr/bin/env bash
# Read-only precheck for a target cluster, run BEFORE scripts/bootstrap.sh.
# Every check here inspects; none of them install an operator, apply a
# manifest, or otherwise mutate cluster state, except the two narrow,
# explicitly opt-in exceptions gated behind --allow-scratch-ns (a
# throwaway PVC bind test and a pod-based outbound-reachability probe,
# both created in and cleaned up from a dedicated scratch namespace).
#
# Requires an explicit --context (ADR-010) -- never relies on kubeconfig's
# ambient current-context, since a concurrent, unrelated `oc login`
# elsewhere on the same machine can silently redirect it mid-session.
#
# docs/cluster-profile.md (once it exists) is meant to be derived from
# this script's own output on a real cluster, not hand-written -- this
# is the "how were these expected values checked" tool for the pins
# recorded in PINS.md, not a one-off.
#
# Usage:
#   tools/cluster_precheck.sh --context <kubeconfig-context> [options]
#
# Options:
#   --context NAME       Required. Exact kubeconfig context name (see
#                         `oc config get-contexts`). Every oc invocation
#                         in this script pins this context explicitly.
#   --allow-scratch-ns    Opt in to the two checks that need to create
#                         (and clean up) throwaway resources in a
#                         dedicated scratch namespace: a PVC bind test
#                         and a pod-based outbound-reachability probe.
#                         Without this flag those two checks are
#                         inspect-only and report WARN (untested), never
#                         FAIL, since absence of the flag is not itself
#                         a cluster problem.
#   --output PATH         Also write the markdown report to PATH (stdout
#                         always gets it either way).
#   -h, --help             Show this help and exit.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CONTEXT=""
ALLOW_SCRATCH_NS=false
OUTPUT_PATH=""

usage() {
  sed -n '2,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --context) CONTEXT="${2:-}"; shift 2 ;;
    --allow-scratch-ns) ALLOW_SCRATCH_NS=true; shift ;;
    --output) OUTPUT_PATH="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

if [ -z "$CONTEXT" ]; then
  echo "FAIL: --context is required (ADR-010) -- no ambient current-context fallback." >&2
  usage
fi

OC="oc --context=$CONTEXT"
if ! $OC whoami >/dev/null 2>&1; then
  echo "FAIL: cannot reach context '$CONTEXT' (oc whoami failed). Check 'oc config get-contexts'." >&2
  exit 1
fi

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

out() { printf '%s\n' "$*" >>"$OUT"; }

row() {
  # row <STATUS> <check-label> <observed> <expected> <detail>
  local status="$1" label="$2" observed="$3" expected="$4" detail="${5:-}"
  case "$status" in
    PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    WARN) WARN_COUNT=$((WARN_COUNT + 1)) ;;
    FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
  esac
  out "| $label | **$status** | $observed | $expected | $detail |"
}

section() {
  out ""
  out "## $1"
  out ""
  out "| Check | Status | Observed | Expected | Detail |"
  out "|---|---|---|---|---|"
}

md_escape() { printf '%s' "$1" | tr '\n' ' ' | sed 's/|/\\|/g'; }

out "# SNO precheck report"
out ""
out "- Context: \`$CONTEXT\`"
out "- API server: \`$($OC whoami --show-server 2>/dev/null)\`"
out "- Run as: \`$($OC whoami 2>/dev/null)\`"
out "- Run at (UTC): \`$(date -u '+%Y-%m-%d %H:%M:%S')\`"
out "- --allow-scratch-ns: \`$ALLOW_SCRATCH_NS\`"

# =============================================================================
section "Cluster health"
# =============================================================================

cv_json="$($OC get clusterversion version -o json 2>/dev/null)"
if [ -z "$cv_json" ]; then
  row FAIL "ClusterVersion reachable" "(no response)" "reachable" "oc get clusterversion failed"
else
  cv_avail="$(echo "$cv_json" | jq -r '.status.conditions[] | select(.type=="Available") | .status')"
  cv_degraded_count="$(echo "$cv_json" | jq -r '.status.conditions[] | select(.type=="Failing" and .status=="True") | .type' | wc -l)"
  if [ "$cv_avail" = "True" ]; then
    row PASS "ClusterVersion Available" "True" "True" ""
  else
    row FAIL "ClusterVersion Available" "$cv_avail" "True" ""
  fi
fi

co_json="$($OC get co -o json 2>/dev/null)"
if [ -z "$co_json" ]; then
  row FAIL "ClusterOperators reachable" "(no response)" "reachable" "oc get co failed"
else
  co_not_available="$(echo "$co_json" | jq -r '.items[] | select(.status.conditions[]? | select(.type=="Available" and .status!="True")) | .metadata.name' | tr '\n' ',' | sed 's/,$//')"
  co_degraded="$(echo "$co_json" | jq -r '.items[] | select(.status.conditions[]? | select(.type=="Degraded" and .status=="True")) | .metadata.name' | tr '\n' ',' | sed 's/,$//')"
  co_total="$(echo "$co_json" | jq -r '.items | length')"
  if [ -z "$co_not_available" ] && [ -z "$co_degraded" ]; then
    row PASS "ClusterOperators (${co_total} total)" "all Available, none Degraded" "all Available, none Degraded" ""
  else
    row FAIL "ClusterOperators (${co_total} total)" "not-available=[${co_not_available}] degraded=[${co_degraded}]" "all Available, none Degraded" ""
  fi
fi

nodes_json="$($OC get nodes -o json 2>/dev/null)"
if [ -z "$nodes_json" ]; then
  row FAIL "Nodes reachable" "(no response)" "reachable" "oc get nodes failed"
else
  not_ready="$(echo "$nodes_json" | jq -r '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status!="True")) | .metadata.name' | tr '\n' ',' | sed 's/,$//')"
  node_count="$(echo "$nodes_json" | jq -r '.items | length')"
  if [ -z "$not_ready" ]; then
    row PASS "Nodes Ready (${node_count} total)" "all Ready" "all Ready" ""
  else
    row FAIL "Nodes Ready (${node_count} total)" "not-ready=[${not_ready}]" "all Ready" ""
  fi
fi

pending_csrs="$($OC get csr -o json 2>/dev/null | jq -r '[.items[] | select(.status == {} )] | length' 2>/dev/null)"
pending_csr_names="$($OC get csr 2>/dev/null | grep -i pending | awk '{print $1}' | tr '\n' ',' | sed 's/,$//')"
if [ -z "$pending_csr_names" ]; then
  row PASS "Pending CSRs" "0" "0 (or owner-approved)" "not approving automatically -- owner decision"
else
  csr_n="$(echo "$pending_csr_names" | tr ',' '\n' | grep -c .)"
  row WARN "Pending CSRs" "${csr_n}: ${pending_csr_names}" "0 (or owner-approved)" "NOT approved by this script -- a long-powered-off SNO often needs kubelet-serving CSR approval; owner decides"
fi

node_time="$($OC debug node/"$($OC get nodes -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)" -- chroot /host date -u '+%Y-%m-%d %H:%M:%S' 2>/dev/null | tail -1)"
if [ -n "$node_time" ]; then
  local_time="$(date -u '+%Y-%m-%d %H:%M:%S')"
  row WARN "Node clock vs. local time" "node=${node_time} local=${local_time}" "within a few seconds" "compare manually -- oc debug node used (creates a short-lived debug pod, standard oc mechanism, auto-cleaned)"
else
  row WARN "Node clock vs. local time" "(not checked)" "within a few seconds" "oc debug node/<node> did not return a value"
fi

api_cert_expiry="$(echo | timeout 10 openssl s_client -connect "$(echo "$($OC whoami --show-server 2>/dev/null)" | sed -e 's#https://##' -e 's#:6443##'):6443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | sed 's/notAfter=//')"
if [ -n "$api_cert_expiry" ]; then
  row WARN "API server cert expiry" "$api_cert_expiry" "not expired, comfortable margin" "compare manually against current date"
else
  row WARN "API server cert expiry" "(could not retrieve)" "not expired" "openssl s_client probe failed or timed out"
fi

# =============================================================================
section "Version and catalog compatibility"
# =============================================================================

current_ocp="$(echo "$cv_json" | jq -r '.status.desired.version' 2>/dev/null)"
progressing="$(echo "$cv_json" | jq -r '.status.conditions[] | select(.type=="Progressing") | .status' 2>/dev/null)"
update_available="$(echo "$cv_json" | jq -r '.status.availableUpdates // [] | length' 2>/dev/null)"
if [ "$current_ocp" = "4.20.23" ]; then
  row PASS "OCP version" "$current_ocp" "4.20.23 (last known; sandbox was 4.21.28)" "Progressing=$progressing, ${update_available} update(s) available in-channel"
else
  row WARN "OCP version" "$current_ocp" "4.20.23 (last known; sandbox was 4.21.28)" "Progressing=$progressing, ${update_available} update(s) available -- re-verify all pins below against this actual version"
fi

catalog_json="$($OC get packagemanifest -n openshift-marketplace -o json 2>/dev/null)"

version_ge() {
  # $1 >= $2, dotted-version comparison (GNU sort -V). Good enough for
  # the "at least this version" comparisons this script needs -- not a
  # full semver implementation.
  [ "$1" = "$2" ] && return 0
  [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" = "$1" ]
}

check_operator_pin() {
  # check_operator_pin <package> <expected-channel> <minimum-version>
  #
  # Exact-CSV pins are brittle across clusters: catalogs prune old
  # entries and rotate forward independently of this project's own
  # release cadence, and an adopter's cluster may already have a newer
  # (still perfectly usable) CSV installed within the same channel.
  # This checks the channel's current head meets a minimum version, not
  # that one exact historical CSV name is still resolvable.
  local pkg="$1" chan="$2" min_version="$3"
  local pm
  pm="$(echo "$catalog_json" | jq -c --arg pkg "$pkg" '.items[] | select(.metadata.name==$pkg and (.status.catalogSource=="redhat-operators"))' 2>/dev/null | head -1)"
  if [ -z "$pm" ]; then
    row FAIL "$pkg in redhat-operators catalog" "not found" "present" "PackageManifest '$pkg' not found in redhat-operators catalog on this cluster"
    return
  fi
  local chan_present current_csv current_version
  chan_present="$(echo "$pm" | jq -r --arg c "$chan" '[.status.channels[].name] | index($c) != null')"
  if [ "$chan_present" != "true" ]; then
    row FAIL "$pkg channel '$chan'" "not present" "present" "available channels: $(echo "$pm" | jq -r '[.status.channels[].name] | join(", ")')"
    return
  fi
  current_csv="$(echo "$pm" | jq -r --arg c "$chan" '.status.channels[] | select(.name==$c) | .currentCSV')"
  current_version="${current_csv##*.v}"
  if version_ge "$current_version" "$min_version"; then
    row PASS "$pkg channel '$chan' minimum version" "head is $current_csv (>= $min_version)" ">= $min_version" ""
  else
    row FAIL "$pkg channel '$chan' minimum version" "head is $current_csv (< $min_version)" ">= $min_version" "channel's current head has fallen below this blueprint's minimum -- re-verify before running scripts/bootstrap.sh"
  fi
}

if [ -z "$catalog_json" ]; then
  row FAIL "redhat-operators catalog reachable" "(no response)" "reachable" "oc get packagemanifest failed"
else
  check_operator_pin "openshift-pipelines-operator-rh" "pipelines-1.22" "1.22.5"
  check_operator_pin "openshift-gitops-operator" "gitops-1.20" "1.20.6"
  check_operator_pin "rhbk-operator" "stable-v26.6" "26.6.6-opr.1"
  check_operator_pin "rhdh" "fast-1.10" "1.10.3"

  rhdh_modes="$(echo "$catalog_json" | jq -r '.items[] | select(.metadata.name=="rhdh" and .status.catalogSource=="redhat-operators") | .status.channels[0].currentCSVDesc.installModes[]? | select(.supported==true) | .type' 2>/dev/null | tr '\n' ',' | sed 's/,$//')"
  if echo "$rhdh_modes" | grep -q "AllNamespaces"; then
    row PASS "RHDH install modes" "$rhdh_modes" "AllNamespaces supported" ""
  else
    row FAIL "RHDH install modes" "$rhdh_modes" "AllNamespaces supported" "required install mode not supported on this catalog's CSV"
  fi
fi

existing_csvs="$($OC get csv -A -o json 2>/dev/null)"
if [ -n "$existing_csvs" ]; then
  # A cluster-wide (AllNamespaces) operator's CSV is copied by OLM into
  # EVERY namespace on the cluster -- `oc get csv -A` on a busy shared
  # cluster returns one row per (operator, namespace) pair, not one row
  # per real install. Report unique CSV names only; a namespace-by-
  # namespace breakdown belongs in a live `oc get csv -A` run, not this
  # summary row.
  csv_total="$(echo "$existing_csvs" | jq -r '.items | length')"
  csv_unique_summary="$(echo "$existing_csvs" | jq -r '[.items[] | .metadata.name] | unique | .[]' | tr '\n' ';' | sed 's/;$//')"
  csv_unique_count="$(echo "$existing_csvs" | jq -r '[.items[] | .metadata.name] | unique | length')"
  keycloak_leftover="$(echo "$existing_csvs" | jq -r '[.items[] | select(.metadata.name | test("keycloak"; "i")) | .metadata.name] | unique | .[]' | tr '\n' ',' | sed 's/,$//')"
  row WARN "Existing CSVs, unique names (${csv_unique_count} unique / ${csv_total} raw rows across all namespaces)" "$(md_escape "$csv_unique_summary")" "reviewed manually" "raw count includes one copy per namespace per cluster-wide operator (OLM's own CSV-mirroring behavior on a shared cluster) -- this row deduplicates by name"

  subs_json="$($OC get subscription -A -o json 2>/dev/null)"
  sub_summary="$(echo "$subs_json" | jq -r '.items[] | "\(.metadata.namespace)/\(.metadata.name)->\(.spec.channel)"' | tr '\n' ';' | sed 's/;$//')"
  row WARN "Existing Subscriptions across all namespaces ($(echo "$subs_json" | jq -r '.items | length'))" "$(md_escape "$sub_summary")" "reviewed manually" "real objects, not copied per-namespace -- this list is exhaustive"

  rhdh_sub_channel="$(echo "$subs_json" | jq -r '.items[] | select(.metadata.name=="rhdh-operator") | .spec.channel' 2>/dev/null)"
  if [ -n "$rhdh_sub_channel" ]; then
    if [ "$rhdh_sub_channel" = "fast-1.10" ]; then
      row PASS "Existing rhdh-operator Subscription channel" "$rhdh_sub_channel" "fast-1.10 (this blueprint's own pin)" ""
    else
      row WARN "Existing rhdh-operator Subscription channel" "$rhdh_sub_channel" "fast-1.10 (this blueprint's own pin)" "an rhdh-operator Subscription already exists on a different channel -- owner-confirmed resolution: update this existing Subscription's channel at bootstrap time rather than creating a second one; not a blocker, but scripts/bootstrap.sh's own RHDH step needs to patch, not blind-apply, this specific object"
    fi
  fi

  if [ -n "$keycloak_leftover" ]; then
    row WARN "CSV names matching 'keycloak' (deduplicated)" "$keycloak_leftover" "none, or reconciled with the OLM RHBK install plan" "name-match only, not proof of a real per-namespace install (see CSV-mirroring note above) -- no keycloak/rhbk Subscription was found in the Subscriptions list above, consistent with this project's history of using the upstream-kustomize Keycloak path (ADR-017) rather than OLM for Keycloak specifically. See the direct CR check below for the real signal"
  else
    row PASS "CSV names matching 'keycloak'" "none found" "none" ""
  fi

  real_keycloak_crs="$($OC get keycloaks.k8s.keycloak.org -A -o json 2>/dev/null | jq -r '.items[] | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null | tr '\n' ',' | sed 's/,$//')"
  if [ -n "$real_keycloak_crs" ]; then
    row WARN "Real Keycloak CRs (k8s.keycloak.org)" "$real_keycloak_crs" "none, or reconciled with the OLM RHBK install plan" "this IS a real per-namespace install, not a CSV-mirroring artifact -- likely the D2 upstream-kustomize path (ADR-017); would conflict with an OLM rhbk-operator install targeting the same namespace"
  else
    row PASS "Real Keycloak CRs (k8s.keycloak.org)" "none found" "none" "checked directly (not name-matching), the CRD may simply not exist yet if no Keycloak operator has ever reconciled on this cluster"
  fi
else
  row WARN "Existing CSVs across all namespaces" "(could not list)" "reviewed manually" "oc get csv -A failed or returned nothing"
fi

# =============================================================================
section "Capacity"
# =============================================================================

alloc_json="$($OC get nodes -o json 2>/dev/null | jq '[.items[].status.allocatable]')"
all_pods_requests_json="$($OC get pods -A -o json 2>/dev/null)"

python3 - "$REPO_ROOT" <<'PYEOF' >"$SCRIPT_DIR/.precheck_capacity.tmp" 2>/dev/null || true
import json, re, sys, subprocess
from pathlib import Path

repo_root = Path(sys.argv[1])

def parse_qty(s):
    """Parse a Kubernetes CPU or memory quantity into a float in base units
    (cores for CPU, bytes for memory)."""
    if s is None:
        return 0.0
    s = str(s)
    m = re.match(r'^([0-9.]+)([a-zA-Z]*)$', s)
    if not m:
        return 0.0
    val, unit = float(m.group(1)), m.group(2)
    mult = {
        '': 1, 'm': 1e-3,
        'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12,
        'Ki': 2**10, 'Mi': 2**20, 'Gi': 2**30, 'Ti': 2**40,
    }
    return val * mult.get(unit, 1)

def sum_requests_from_manifests(paths):
    import yaml
    cpu = mem = 0.0
    found = []
    for p in paths:
        try:
            docs = list(yaml.safe_load_all(p.read_text()))
        except Exception:
            continue
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            containers = []
            spec = doc.get('spec', {})
            tmpl = spec.get('template', {}).get('spec', {}) if isinstance(spec, dict) else {}
            containers += tmpl.get('containers', []) or []
            containers += tmpl.get('initContainers', []) or []
            for c in containers:
                req = (c.get('resources') or {}).get('requests') or {}
                if req:
                    c_cpu = parse_qty(req.get('cpu'))
                    c_mem = parse_qty(req.get('memory'))
                    cpu += c_cpu
                    mem += c_mem
                    found.append((str(p.relative_to(repo_root)), c.get('name'), req.get('cpu'), req.get('memory')))
    return cpu, mem, found

paths = list((repo_root / 'platform' / 'bootstrap').rglob('*.yaml')) + \
        list((repo_root / 'deploy').rglob('*.yaml'))
cpu, mem, found = sum_requests_from_manifests(paths)
print(json.dumps({'cpu_cores': cpu, 'mem_bytes': mem, 'count': len(found), 'items': found}))
PYEOF

if [ -s "$SCRIPT_DIR/.precheck_capacity.tmp" ]; then
  cap_data="$(cat "$SCRIPT_DIR/.precheck_capacity.tmp")"
  rm -f "$SCRIPT_DIR/.precheck_capacity.tmp"
  req_cpu="$(echo "$cap_data" | jq -r '.cpu_cores')"
  req_mem_gi="$(echo "$cap_data" | jq -r '.mem_bytes / 1073741824 | round')"
  container_count="$(echo "$cap_data" | jq -r '.count')"

  alloc_cpu="$(echo "$alloc_json" | jq -r '[.[].cpu | sub("m$";"") | if test("m$") then . else (tonumber*1000|tostring) end] | map(tonumber) | add' 2>/dev/null)"
  # simpler: sum allocatable cpu (cores) and memory (bytes) via python for correctness
  alloc_summary="$(echo "$alloc_json" | python3 -c "
import json,sys,re
def parse_qty(s):
    m = re.match(r'^([0-9.]+)([a-zA-Z]*)\$', str(s))
    if not m: return 0.0
    val, unit = float(m.group(1)), m.group(2)
    mult = {'':1,'m':1e-3,'K':1e3,'M':1e6,'G':1e9,'T':1e12,'Ki':2**10,'Mi':2**20,'Gi':2**30,'Ti':2**40}
    return val * mult.get(unit,1)
data = json.load(sys.stdin)
cpu = sum(parse_qty(n.get('cpu')) for n in data)
mem = sum(parse_qty(n.get('memory')) for n in data)
print(f'{cpu:.2f} {mem/1073741824:.1f}')
")"
  alloc_cpu_cores="$(echo "$alloc_summary" | awk '{print $1}')"
  alloc_mem_gi="$(echo "$alloc_summary" | awk '{print $2}')"

  current_used_summary="$(echo "$all_pods_requests_json" | python3 -c "
import json,sys,re
def parse_qty(s):
    if s is None: return 0.0
    m = re.match(r'^([0-9.]+)([a-zA-Z]*)\$', str(s))
    if not m: return 0.0
    val, unit = float(m.group(1)), m.group(2)
    mult = {'':1,'m':1e-3,'K':1e3,'M':1e6,'G':1e9,'T':1e12,'Ki':2**10,'Mi':2**20,'Gi':2**30,'Ti':2**40}
    return val * mult.get(unit,1)
data = json.load(sys.stdin)
cpu = mem = 0.0
for pod in data.get('items', []):
    if pod.get('status',{}).get('phase') not in ('Running','Pending'):
        continue
    for c in pod.get('spec',{}).get('containers', []):
        req = (c.get('resources') or {}).get('requests') or {}
        cpu += parse_qty(req.get('cpu'))
        mem += parse_qty(req.get('memory'))
print(f'{cpu:.2f} {mem/1073741824:.1f}')
")"
  used_cpu_cores="$(echo "$current_used_summary" | awk '{print $1}')"
  used_mem_gi="$(echo "$current_used_summary" | awk '{print $2}')"

  headroom_cpu="$(python3 -c "print(f'{${alloc_cpu_cores:-0} - ${used_cpu_cores:-0} - ${req_cpu:-0}:.2f}')" 2>/dev/null)"
  headroom_mem="$(python3 -c "print(f'{${alloc_mem_gi:-0} - ${used_mem_gi:-0} - ${req_mem_gi:-0}:.1f}')" 2>/dev/null)"

  row WARN "Node allocatable CPU (cores)" "${alloc_cpu_cores}" "n/a" "already-used=${used_cpu_cores}; blueprint's own committed requests=${req_cpu} (from ${container_count} containers across platform/bootstrap/+deploy/, static analysis -- excludes operator-injected defaults for Keycloak/RHDH/Pipelines/GitOps/OTel CRs, which aren't statically pinned in these manifests)"
  row WARN "Node allocatable memory (Gi)" "${alloc_mem_gi}" "n/a" "already-used=${used_mem_gi}; blueprint's own committed requests=${req_mem_gi}"
  if python3 -c "exit(0 if ${headroom_cpu:-0} > 0 else 1)" 2>/dev/null; then
    row PASS "CPU headroom after this blueprint's own requests" "${headroom_cpu} cores free" "> 0" "static estimate only -- does not include operator-managed CR defaults, see detail above"
  else
    row FAIL "CPU headroom after this blueprint's own requests" "${headroom_cpu} cores free" "> 0" "insufficient by static estimate -- also does not yet include operator-managed CR defaults, which would make this worse, not better"
  fi
  if python3 -c "exit(0 if ${headroom_mem:-0} > 0 else 1)" 2>/dev/null; then
    row PASS "Memory headroom after this blueprint's own requests" "${headroom_mem} Gi free" "> 0" "static estimate only, see detail above"
  else
    row FAIL "Memory headroom after this blueprint's own requests" "${headroom_mem} Gi free" "> 0" "insufficient by static estimate"
  fi
else
  row WARN "Capacity computation" "(failed)" "n/a" "python3/yaml manifest walk did not produce output -- see script stderr"
fi

sc_json="$($OC get storageclass -o json 2>/dev/null)"
default_sc="$(echo "$sc_json" | jq -r '.items[] | select(.metadata.annotations["storageclass.kubernetes.io/is-default-class"]=="true") | .metadata.name' 2>/dev/null)"
default_sc_provisioner="$(echo "$sc_json" | jq -r --arg n "$default_sc" '.items[] | select(.metadata.name==$n) | .provisioner' 2>/dev/null)"
if [ -n "$default_sc" ]; then
  row PASS "Default StorageClass" "$default_sc ($default_sc_provisioner)" "present" ""
else
  row FAIL "Default StorageClass" "none marked default" "present" "no StorageClass has the is-default-class annotation"
fi

if [ "$ALLOW_SCRATCH_NS" = true ]; then
  SCRATCH_NS="cluster-precheck-scratch-$$"
  if $OC create namespace "$SCRATCH_NS" >/dev/null 2>&1; then
    cat <<EOF | $OC apply -n "$SCRATCH_NS" -f - >/dev/null 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: precheck-rwo-test
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
EOF
    sleep 5
    pvc_phase="$($OC get pvc precheck-rwo-test -n "$SCRATCH_NS" -o jsonpath='{.status.phase}' 2>/dev/null)"
    if [ "$pvc_phase" = "Bound" ]; then
      row PASS "RWO PVC bind test" "Bound" "Bound" "scratch namespace $SCRATCH_NS, cleaned up"
    else
      row WARN "RWO PVC bind test" "phase=$pvc_phase after 5s" "Bound" "may just need more time for a dynamic provisioner -- not a hard FAIL from a single short wait"
    fi
    $OC delete namespace "$SCRATCH_NS" >/dev/null 2>&1 &
  else
    row WARN "RWO PVC bind test" "(could not create scratch namespace)" "Bound" "namespace creation failed -- inspect-only fallback not re-attempted"
  fi
else
  row WARN "RWO PVC bind test" "not tested" "Bound" "pass --allow-scratch-ns to run a real dynamic-provisioning test in a throwaway namespace"
fi

registry_json="$($OC get configs.imageregistry.operator.openshift.io/cluster -o json 2>/dev/null)"
if [ -n "$registry_json" ]; then
  mgmt_state="$(echo "$registry_json" | jq -r '.spec.managementState')"
  storage_kind="$(echo "$registry_json" | jq -r '.spec.storage | to_entries | map(select(.key != "managementState")) | .[0].key // "none"')"
  route_host="$($OC get route -n openshift-image-registry -o jsonpath='{.items[?(@.metadata.name=="default-route")].spec.host}' 2>/dev/null)"
  pvc_claim="$(echo "$registry_json" | jq -r '.spec.storage.pvc.claim // empty')"
  storage_phase="unknown"
  if [ -n "$pvc_claim" ]; then
    storage_phase="$($OC get pvc "$pvc_claim" -n openshift-image-registry -o jsonpath='{.status.phase}' 2>/dev/null)"
  fi
  if [ "$mgmt_state" = "Managed" ] && [ -n "$route_host" ] && [ "$storage_phase" = "Bound" ]; then
    row PASS "Internal registry" "Managed, storage=$storage_kind ($storage_phase), route=$route_host" "Managed, storage bound, route exposed" ""
  else
    row WARN "Internal registry" "managementState=$mgmt_state storage=$storage_kind (phase=$storage_phase) route=${route_host:-none}" "Managed, storage bound, route exposed" ""
  fi
else
  row FAIL "Internal registry" "(no response)" "Managed, storage bound, route exposed" "oc get configs.imageregistry.operator.openshift.io/cluster failed"
fi

# =============================================================================
section "Leftover state"
# =============================================================================

leftover_ns="$($OC get namespace -o json 2>/dev/null | jq -r '.items[] | select(.metadata.name | test("^golden-path-|-keycloak$|-ci$")) | .metadata.name' | tr '\n' ',' | sed 's/,$//')"
if [ -n "$leftover_ns" ]; then
  row WARN "Leftover project namespaces" "$leftover_ns" "owner decides: clean-slate or reuse" "listed only -- this script does not delete anything"
else
  row PASS "Leftover project namespaces" "none found" "none, or owner-reviewed" ""
fi

argocd_apps="$($OC get applications.argoproj.io -A -o json 2>/dev/null)"
if [ -n "$argocd_apps" ]; then
  # Scoped to this project's own exact Application name
  # (deploy/argocd/application-root.yaml's own metadata.name) -- a
  # generic "root" substring match would also catch an unrelated
  # tenant's own cluster-bootstrap Application on a shared cluster.
  root_app="$(echo "$argocd_apps" | jq -r '.items[] | select(.metadata.name=="golden-path-agent-root") | "\(.metadata.namespace)/\(.metadata.name): sync=\(.status.sync.status // "?") health=\(.status.health.status // "?") automated=\(.spec.syncPolicy.automated != null)"')"
  other_root_named="$(echo "$argocd_apps" | jq -r '.items[] | select(.metadata.name != "golden-path-agent-root" and (.metadata.name | test("root"))) | .metadata.name' | tr '\n' ',' | sed 's/,$//')"
  if [ -n "$root_app" ]; then
    row WARN "ArgoCD root Application (golden-path-agent-root)" "$(md_escape "$root_app")" "present, auto-sync OFF (deprotected per ADR-009)" "verify automated=false against ADR-009's expectation"
  else
    row WARN "ArgoCD root Application (golden-path-agent-root)" "not found" "present, auto-sync OFF (deprotected per ADR-009)" "no Application named exactly golden-path-agent-root"
  fi
  if [ -n "$other_root_named" ]; then
    row WARN "Other 'root'-named ArgoCD Applications (unrelated to this project)" "$other_root_named" "n/a, informational" "not this project's own resource -- likely this shared cluster's own baseline/tenant GitOps root(s), do not touch"
  fi
else
  row WARN "ArgoCD root Application" "(could not list, or ArgoCD not installed)" "present, auto-sync OFF" ""
fi

# =============================================================================
section "Environment"
# =============================================================================

apps_domain="$($OC get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' 2>/dev/null)"
if [ -n "$apps_domain" ]; then
  # apps_domain already carries the full apps.<cluster-domain> form (per
  # ingresses.config's own .spec.domain semantics) -- no separate "apps."
  # prefix to prepend.
  if getent hosts "console-openshift-console.$apps_domain" >/dev/null 2>&1 || host "console-openshift-console.$apps_domain" >/dev/null 2>&1; then
    row PASS "Apps domain DNS resolution" "*.$apps_domain resolves from this machine" "resolvable" "DNS-only proxy for 'browser-resolvable' -- owner should still confirm in an actual browser on their own network"
  else
    row WARN "Apps domain DNS resolution" "*.$apps_domain did NOT resolve from this machine" "resolvable" "may still resolve from the owner's own browser/network even if not from here -- needs owner confirmation either way"
  fi
else
  row FAIL "Apps domain" "(could not determine)" "resolvable" "oc get ingresses.config.openshift.io cluster failed"
fi

if [ "$ALLOW_SCRATCH_NS" = true ]; then
  PROBE_NS="cluster-precheck-egress-$$"
  if $OC create namespace "$PROBE_NS" >/dev/null 2>&1; then
    $OC run precheck-egress --image=registry.access.redhat.com/ubi9/ubi-minimal:latest -n "$PROBE_NS" --restart=Never \
      --command -- /bin/sh -c 'sleep 60' >/dev/null 2>&1
    sleep 8
    for host in registry.redhat.io quay.io github.com; do
      if $OC exec -n "$PROBE_NS" precheck-egress -- curl -s -o /dev/null -m 5 -w '%{http_code}' "https://$host" 2>/dev/null | grep -qE '^[23][0-9]{2}$'; then
        row PASS "Outbound reachability: $host" "reachable" "reachable" "probed from a throwaway pod in $PROBE_NS"
      else
        row WARN "Outbound reachability: $host" "not confirmed reachable" "reachable" "probe pod may not have been Ready yet, or egress is genuinely blocked -- re-run if uncertain"
      fi
    done
    $OC delete namespace "$PROBE_NS" >/dev/null 2>&1 &
  else
    row WARN "Outbound reachability probe" "(could not create scratch namespace)" "reachable" "namespace creation failed"
  fi
else
  row WARN "Outbound reachability: registry.redhat.io, quay.io, github.com" "not tested" "reachable" "pass --allow-scratch-ns to run a real pod-based probe"
fi

row WARN "Model endpoint (OpenAI-compatible)" "no endpoint configured on this cluster; skeleton/.env.example points at localhost:11434, a local-machine default" "an explicit adopter decision" "ACTION NEEDED: this script does not assume one -- the owner must say which OpenAI-compatible endpoint (MaaS route, a model served on this cluster, or elsewhere) MODEL_API_BASE_URL should point at before any live run"

# =============================================================================
out ""
out "## Summary"
out ""
out "PASS: $PASS_COUNT, WARN: $WARN_COUNT, FAIL: $FAIL_COUNT"
out ""
out "This script never approves a CSR, deletes a namespace, or picks a"
out "model endpoint -- those are owner decisions, surfaced above, not"
out "made here."
# =============================================================================

if [ -n "$OUTPUT_PATH" ]; then
  cp "$OUT" "$OUTPUT_PATH"
fi
cat "$OUT"

[ "$FAIL_COUNT" -eq 0 ]
