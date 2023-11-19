import os

import pytest

from ragna.deploy import Config


@pytest.mark.xfail()
def test_explicit_gt_env_var(mocker, tmp_path):
    explicit = tmp_path / "explicit"

    env_var = tmp_path / "env_var"
    mocker.patch.dict(os.environ, values={"RAGNA_LOCAL_CACHE_ROOT": str(env_var)})

    config = Config(local_cache_root=explicit)

    assert config.local_cache_root == explicit


def test_env_var_gt_config_file(mocker, tmp_path):
    config_file = tmp_path / "config_file"
    config = Config(local_cache_root=config_file)
    assert config.local_cache_root == config_file

    config_path = tmp_path / "ragna.toml"
    config.to_file(config_path)

    env_var = tmp_path / "env_var"
    mocker.patch.dict(os.environ, values={"RAGNA_LOCAL_CACHE_ROOT": str(env_var)})

    config = Config.from_file(config_path)

    assert config.local_cache_root == env_var
