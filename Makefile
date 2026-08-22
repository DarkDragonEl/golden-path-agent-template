CONTAINER_ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: build up up-offline down logs eval eval-fast eval-domain validate-eval-set trace test lint

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
eval-fast:
	python -m eval.cli run --all

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
