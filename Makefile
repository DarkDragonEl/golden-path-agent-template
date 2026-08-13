CONTAINER_ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: build up up-offline down logs eval test lint

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

test:
	pytest -q

lint:
	python -m py_compile $$(find agent mcp_server eval -name '*.py')
