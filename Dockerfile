FROM python:3.12

WORKDIR /opt/ragna

COPY requirements-docker.lock .
RUN pip install --progress-bar=off --no-deps --no-cache --requirement requirements-docker.lock

# Pre-download the default embedding model
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()._download_model_if_not_exists()"

COPY ragna ./ragna
COPY pyproject.toml .
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
RUN pip install --progress-bar=off --no-deps .

WORKDIR /var/ragna
# See https://github.com/Quansight/ragna/issues/329
ENV LANCEDB_CONFIG_DIR=/var/ragna/lancedb.config

COPY ragna-docker.toml ragna.toml

ENTRYPOINT ["ragna"]
CMD ["ui", "--start-api", "--ignore-unavailable-components", "--no-open-browser"]
