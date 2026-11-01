# Imagen única del experimento: Python + dbt + DuckDB + Claude Code, con versiones fijas.
#
# La imagen NO contiene el proyecto (ni la referencia ni los metadatos): se monta desde
# afuera según el paso. Así, cuando corre el agente, solo se monta la carpeta de su corrida
# y no tiene forma de ver la solución.
FROM python:3.13.15-slim-bookworm

ARG CLAUDE_CODE_VERSION=2.1.274

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates git ripgrep procps \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Usuario sin privilegios: el agente y los scripts corren como "agente".
RUN useradd -m -u 1000 -s /bin/bash agente
USER agente
ENV HOME=/home/agente \
    PATH=/home/agente/.local/bin:$PATH \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    PYTHONDONTWRITEBYTECODE=1

# Claude Code en versión fija, sin actualizaciones automáticas.
RUN curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_CODE_VERSION} \
 && claude --version

# Evita el asistente de primer uso en el modo interactivo (demo).
COPY --chown=agente:agente docker/claude.json /home/agente/.claude.json

# Script que ejecuta al agente dentro de la carpeta de la corrida.
COPY --chown=agente:agente --chmod=755 docker/agente.sh /home/agente/.local/bin/tasd-agente

WORKDIR /trabajo
