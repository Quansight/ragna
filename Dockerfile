FROM python:3.11

WORKDIR /opt/ragna

COPY requirements.lock ./
RUN pip install --progress-bar=off --no-cache-dir --requirement requirements.lock

ARG WHEEL
COPY "${WHEEL}" .
RUN pip install --progress-bar=off --no-deps *.whl

WORKDIR /var/ragna
ENTRYPOINT []
CMD ["ragna", "--help"]
