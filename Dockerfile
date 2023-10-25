FROM python:3.11
ENTRYPOINT []

WORKDIR /opt/ragna

COPY requirements.lock ./
RUN pip install --progress-bar=off --requirement requirements.lock

COPY ragna ./ragna
COPY pyproject.toml .

# We need to pass this explicitly as
# --build-arg SETUPTOOLS_SCM_PRETEND_VERSION_FOR_RAGNA=...,
# since setuptools-scm otherwise tries to infer the version from the .git folder,
# which we don't copy.
ARG SETUPTOOLS_SCM_PRETEND_VERSION_FOR_RAGNA
RUN pip install --progress-bar=off --no-deps .

WORKDIR /var/ragna
