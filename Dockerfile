FROM debian:latest

RUN apt-get update \
    && apt-get upgrade --yes \
    && apt-get install --yes git python3 python3-pip python3-venv

RUN git clone https://github.com/Quansight/ragna /ragna \
    && cd /ragna \
    && /bin/bash -c "python3 -m venv ~/.venvs/ragna-dev \
        && source ~/.venvs/ragna-dev/bin/activate \
        && pip install .[all]"

RUN echo 'local_cache_root = "/root/.cache/ragna"' >> /ragna/ragna.toml \
    && echo 'document = "ragna.core.LocalDocument"' >> /ragna/ragna.toml \
    && echo 'authentication = "ragna.deploy._authentication.RagnaDemoAuthentication"\n' >> /ragna/ragna.toml \
    && echo '[components]' >> /ragna/ragna.toml \
    && echo 'source_storages = ["ragna.source_storages.RagnaDemoSourceStorage"]' >> /ragna/ragna.toml \
    && echo 'assistants = ["ragna.assistants.RagnaDemoAssistant"]\n' >> /ragna/ragna.toml \
    && echo '[api]' >> /ragna/ragna.toml \
    && echo 'url = "http://0.0.0.0:31476"' >> /ragna/ragna.toml \
    && echo 'origins = ["http://localhost:31477"]' >> /ragna/ragna.toml \
    && echo 'database_url = "memory"\n' >> /ragna/ragna.toml \
    && echo '[ui]' >> /ragna/ragna.toml \
    && echo 'url = "http://0.0.0.0:31477"' >> /ragna/ragna.toml \
    && echo 'origins = ["http://localhost:31477"]' >> /ragna/ragna.toml

WORKDIR /ragna

CMD /bin/bash -c "source ~/.venvs/ragna-dev/bin/activate && ragna ui"
