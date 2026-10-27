# Installed package only; no source checkout, Task or runtime network requirement.
ARG PYTHON_IMAGE=python:3.12.12-slim-bookworm
FROM ${PYTHON_IMAGE} AS python-base

FROM ghcr.io/astral-sh/uv:0.12.23 AS uv-tools

FROM python-base AS development
COPY --from=uv-tools /uv /uvx /usr/local/bin/
ARG TASK_VERSION=3.54.0
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git dpkg-dev && rm -rf /var/lib/apt/lists/*
RUN --mount=type=secret,id=ca,required=false set -eu; \
    if [ -f /run/secrets/ca ]; then export CURL_CA_BUNDLE=/run/secrets/ca; fi; \
    arch="$(dpkg --print-architecture)"; \
    mkdir /tmp/task; cd /tmp/task; \
    curl -fsSLO "https://github.com/go-task/task/releases/download/v${TASK_VERSION}/task_linux_${arch}.tar.gz"; \
    curl -fsSLO "https://github.com/go-task/task/releases/download/v${TASK_VERSION}/task_checksums.txt"; \
    sha256sum --ignore-missing -c task_checksums.txt; \
    tar -xzf "task_linux_${arch}.tar.gz" task; \
    install task /usr/local/bin/task; rm -rf /tmp/task
RUN useradd --create-home --uid 1000 --shell /bin/bash vscode
ENV UV_PROJECT_ENVIRONMENT=/opt/common-venv UV_CACHE_DIR=/opt/common-cache
WORKDIR /workspace/common
RUN mkdir -p /opt/common-venv /opt/common-cache && chmod 1777 /opt/common-venv /opt/common-cache
USER vscode
CMD ["sleep", "infinity"]


# Browser system libraries are development-only; the common library remains pure Python.
FROM development AS documentation-test
USER root
COPY pyproject.toml uv.lock /tmp/common-tools/
RUN cd /tmp/common-tools && \
    UV_PROJECT_ENVIRONMENT=/tmp/common-tools/venv uv sync --locked --no-install-project --group docs-test --no-python-downloads && \
    /tmp/common-tools/venv/bin/playwright install-deps chromium && \
    rm -rf /tmp/common-tools
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/common-browsers
RUN mkdir -p /opt/common-browsers && chmod 1777 /opt/common-browsers
USER vscode
