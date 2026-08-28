#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the approval service,
# nothing else. Retires the three-way positional-arg dispatch
# now that G2 gives each component its
# own image.
set -e
exec uvicorn approval_service.api:app --host 0.0.0.0 --port "${APPROVAL_PORT:-8082}"
