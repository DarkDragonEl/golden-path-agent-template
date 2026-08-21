CONTAINER_ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: build up up-offline down logs eval eval-domain validate-eval-set trace test lint

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

eval:
	python -m eval.cli run --all

# Meaningful only against a real model (AGENT_MODEL_MODE=live) -- domain
# cases exercise real reasoning, tool selection, and citation, which
# FakeModelClient doesn't simulate. Checkpoint B2's exit criterion.
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
