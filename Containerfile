# ARG, not a hardcoded pin: the enterprise-approved base image is supplied
# at build time per engagement/platform. This default is a plain, generic
# image so the scaffold builds and runs anywhere out of the box.
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

WORKDIR /opt/app-root/src

# Dependencies first (cache layer).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code only — never the corpus. The corpus is a mount, not a layer.
COPY agent/ ./agent/
COPY mcp_server/ ./mcp_server/
COPY approval_service/ ./approval_service/
COPY policy/ ./policy/
COPY corpus/ingest.py ./corpus/ingest.py
COPY --chmod=0755 entrypoint.sh ./entrypoint.sh

# Mount points, not baked-in data — see corpus/README.md.
ENV AGENT_CORPUS_DIR=/mnt/corpus \
    AGENT_STATE_DIR=/opt/app-root/src/state \
    AGENT_PORT=8080 \
    MCP_PORT=8081 \
    APPROVAL_PORT=8082

# Restricted-SCC-compatible: arbitrary non-root UID, group-writable, GID 0.
# state/approval is approval_service's own SQLite PVC mount point
# (APPROVAL_DB_PATH default, Phase D Step D1) -- pre-created here so the
# first write doesn't depend on runtime directory-creation working under
# the arbitrary UID (it would, since state/ itself is already g=u/GID 0,
# but this matches the existing AGENT_STATE_DIR/AGENT_CORPUS_DIR
# precedent rather than relying on that implicitly).
RUN mkdir -p "$AGENT_STATE_DIR" "$AGENT_CORPUS_DIR" "$AGENT_STATE_DIR/approval" \
    && chmod -R g=u /opt/app-root/src "$AGENT_CORPUS_DIR"

USER 1001
EXPOSE 8080 8081 8082
ENTRYPOINT ["./entrypoint.sh"]
CMD ["agent"]
