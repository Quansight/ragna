FROM ghcr.io/prefix-dev/pixi:0.45.0-bookworm-slim AS build

WORKDIR /var/ragna

COPY ragna ./ragna
COPY pyproject.toml pixi.lock .
# Since we don't copy the .git folder, but still use setuptools-scm as build-backend
# we need to make two manual changes:
# 1. With setuptools-scm all files that are tracked by git are automatically included in
#    the built wheel. Since we have corresponding .dockerignore file to our .gitignore,
#    the ragna folder only includes files that we are tracking. Thus, we just include
#    everything manually.
# 2. We need to pass the version expliclitly as
#    --build-arg SETUPTOOLS_SCM_PRETEND_VERSION_FOR_RAGNA=...,
#    since setuptools-scm cannot infer the version
RUN echo '[tool.setuptools.package-data]\n"*" = ["*"]' >> pyproject.toml
ARG SETUPTOOLS_SCM_PRETEND_VERSION_FOR_RAGNA
ARG ENVIRONMENT="default-all-py312"

RUN <<EOF
pixi shell-hook --frozen -e $ENVIRONMENT -s bash > /shell-hook.sh;
echo "#!/bin/bash" > /entrypoint.sh;
cat /shell-hook.sh >> /entrypoint.sh;
echo 'exec "$@"' >> /entrypoint.sh;
EOF

RUN pixi install --frozen -e $ENVIRONMENT

FROM debian:bookworm-slim AS runtime

RUN useradd --create-home --shell "$(which bash)" ragna
USER ragna

WORKDIR /var/ragna

COPY --from=build --chown=ragna:ragna /var/ragna/.pixi/envs/default-all-py312 /var/ragna/.pixi/envs/default-all-py312
COPY --from=build --chown=ragna:ragna --chmod=0755 /entrypoint.sh /entrypoint.sh
COPY --from=build --chown=ragna:ragna /var/ragna/ragna /var/ragna/ragna

# See https://github.com/Quansight/ragna/issues/329
ENV LANCEDB_CONFIG_DIR=/var/ragna/lancedb.config

COPY ragna-docker.toml ragna.toml

# Pre-download the default embedding model
RUN /entrypoint.sh python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()._download_model_if_not_exists()"

ENTRYPOINT ["/entrypoint.sh", "ragna"]
CMD ["deploy", "--ui", "--api", "--ignore-unavailable-components", "--no-open-browser"]
