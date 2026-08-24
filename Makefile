CONTAINER_ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: build up up-offline down logs eval eval-fast eval-domain validate-eval-set trace test lint bootstrap

build:
	$(CONTAINER_ENGINE) build -t golden-path-agent:dev .

up:
	./scripts/dev.sh up

up-offline:
	./scripts/dev.sh up --offline

down:
	./scripts/dev.sh down

logs:
	./scripts/dev.sh logs

# R0 crosswalk / DEC-020: the canonical target now runs the real gate --
# EXAMPLE-*.yaml fixtures + all 8 domain categories, DEC-017's gate
# semantics (deterministic sampling, named known-gap/measurement-tolerance
# exclusions) applied. Meaningful only against a real model
# (AGENT_MODEL_MODE=live) -- domain cases exercise real reasoning, tool
# selection, and citation, which FakeModelClient doesn't simulate.
# Checkpoint B2's exit criterion -- "make up && make eval" now actually
# tests what that command has always claimed to.
eval: eval-fast eval-domain

# Fast, fully offline EXAMPLE-*.yaml harness-mechanics smoke pair -- inner-
# loop dev iteration only, not the promotion gate (that's `eval`, above).
# ci/pr-checks.yaml's PR-check stage runs this exact command directly.
#
# AGENT_MODEL_MODE=fake is forced here, not left to eval/cli.py's own
# os.environ.setdefault (a soft default that does nothing if the caller's
# shell already exported AGENT_MODEL_MODE=live -- exactly what a caller
# running the combined `eval` target after sourcing .env for eval-domain's
# sake would have done. Found by direct verification, not assumed: running
# `eval-fast`/`eval-domain` back to back in a shell with AGENT_MODEL_MODE
# already exported silently broke EXAMPLE-001/002 before this line existed.
# eval-domain intentionally has no such override -- it must keep requiring
# the caller to explicitly opt into live mode, per its own comment below.
eval-fast:
	AGENT_MODEL_MODE=fake python -m eval.cli run --all

# Equivalent to `eval`'s domain half alone -- useful when iterating on a
# domain-only change without re-running the offline EXAMPLE pair.
eval-domain:
	python -m eval.cli run --domain

validate-eval-set:
	python eval/validate.py

trace:
	python tools/trace-check/trace_check.py --docs-only

test:
	pytest -q

lint:
	python -m py_compile $$(find agent mcp_server eval -name '*.py')

# Phase E, E1 (DECISIONS.md DEC-078 onward). Replays the from-scratch
# bootstrap sequence (operators, namespaces, RBAC, Keycloak, cluster-tier
# OTel, ArgoCD app-of-apps root) against any OpenShift cluster whose
# kubeconfig is already authenticated -- CLUSTER=<path>. See
# scripts/bootstrap.sh for the full step list and docs/phase-c-runbook.md
# for the manual secret-provisioning commands it pauses for.
bootstrap:
	./scripts/bootstrap.sh $(CLUSTER)
