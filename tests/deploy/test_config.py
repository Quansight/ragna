import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from ragna.core import RagnaException
from ragna.deploy import Config


def test_env_var_prefix(mocker, tmp_path):
    env_var = tmp_path / "env_var"
    mocker.patch.dict(os.environ, values={"RAGNA_LOCAL_ROOT": str(env_var)})

    config = Config()

    assert config.local_root == env_var


def test_env_var_api_prefix(mocker):
    env_var = "hostname"
    mocker.patch.dict(os.environ, values={"RAGNA_API_HOSTNAME": env_var})

    config = Config()

    assert config.api.hostname == env_var


def test_env_var_ui_prefix(mocker):
    env_var = "hostname"
    mocker.patch.dict(os.environ, values={"RAGNA_UI_HOSTNAME": env_var})

    config = Config()

    assert config.ui.hostname == env_var


@pytest.mark.xfail()
def test_explicit_gt_env_var(mocker, tmp_path):
    explicit = tmp_path / "explicit"

    env_var = tmp_path / "env_var"
    mocker.patch.dict(os.environ, values={"RAGNA_LOCAL_ROOT": str(env_var)})

    config = Config(local_root=explicit)

    assert config.local_root == explicit


def test_env_var_gt_config_file(mocker, tmp_path):
    config_file = tmp_path / "config_file"
    config = Config(local_root=config_file)
    assert config.local_root == config_file

    config_path = tmp_path / "ragna.toml"
    config.to_file(config_path)

    env_var = tmp_path / "env_var"
    mocker.patch.dict(os.environ, values={"RAGNA_LOCAL_ROOT": str(env_var)})

    config = Config.from_file(config_path)

    assert config.local_root == env_var


def test_api_database_url_default_path(tmp_path):
    config = Config(local_root=tmp_path)
    assert Path(urlsplit(config.api.database_url).path[1:]).parent == tmp_path


@pytest.mark.parametrize("config_subsection", ["api", "ui"])
def test_origins_default(config_subsection):
    hostname, port = "0.0.0.0", "80"
    config = Config(ui=dict(hostname=hostname, port=port))

    assert getattr(config, config_subsection).origins == [f"http://{hostname}:{port}"]


def test_from_file_path_not_exists(tmp_path):
    with pytest.raises(RagnaException, match="does not exist"):
        Config.from_file(tmp_path / "ragna.toml")


def test_from_file_path_exists(tmp_path):
    config_path = tmp_path / "ragna.toml"
    open(config_path, "w").close()

    with pytest.raises(RagnaException, match="already exists"):
        Config().to_file(config_path)


def test_from_file_path_exists_force(tmp_path):
    config_path = tmp_path / "ragna.toml"
    open(config_path, "w").close()

    config = Config(local_root=tmp_path)
    config.to_file(config_path, force=True)

    assert Config.from_file(config_path).local_root == tmp_path
