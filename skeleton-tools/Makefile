CONTAINER_ENGINE ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: build up down test lint

build:
	$(CONTAINER_ENGINE) build -t ${{ values.name }}:dev .

# Local dev: the MCP server standalone, no agent/approval counterpart --
# an independent Tools Template instance is meant to be run and tested on
# its own. Point a separately-running agent's
# MCP_TOOL_ENDPOINT at this container's own port to exercise it end to end.
up:
	$(CONTAINER_ENGINE) run --rm -d --name ${{ values.name }}-dev -p 18081:8081 ${{ values.name }}:dev

down:
	$(CONTAINER_ENGINE) rm -f ${{ values.name }}-dev

test:
	pytest -q

lint:
	python -m py_compile $$(find mcp_server -name '*.py')
