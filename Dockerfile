FROM python:3.11

WORKDIR /opt/ragna

COPY requirements.txt .
RUN pip wheel --progress-bar=off --requirement requirements.txt

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
RUN pip install --progress-bar=off .[vectordb]

WORKDIR /var/ragna
COPY ragna-docker.toml ragna.toml
ENV RAGNA_CONFIG=/var/ragna/ragna.toml

ENTRYPOINT []
CMD ["ragna", "--help"]