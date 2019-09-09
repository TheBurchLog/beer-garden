from __future__ import unicode_literals

import json
import os
from io import open
from ruamel import yaml

import pytest
from box import Box
from mock import patch, Mock
from yapconf import YapconfSpec

import beer_garden.bg_utils
import beer_garden.bg_utils.mongo.models


@pytest.fixture
def spec():
    return YapconfSpec(
        {
            "log": {
                "type": "dict",
                "items": {
                    "config_file": {
                        "type": "str",
                        "description": "Path to a logging config file.",
                        "required": False,
                        "cli_short_name": "l",
                        "previous_names": ["log_config"],
                        "alt_env_names": ["LOG_CONFIG"],
                    },
                    "file": {
                        "type": "str",
                        "description": "File you would like the application to log to",
                        "required": False,
                        "previous_names": ["log_file"],
                    },
                    "level": {
                        "type": "str",
                        "description": "Log level for the application",
                        "default": "INFO",
                        "choices": [
                            "DEBUG",
                            "INFO",
                            "WARN",
                            "WARNING",
                            "ERROR",
                            "CRITICAL",
                        ],
                        "previous_names": ["log_level"],
                    },
                },
            },
            "configuration": {
                "type": "dict",
                "bootstrap": True,
                "items": {
                    "file": {
                        "required": False,
                        "bootstrap": True,
                        "cli_short_name": "c",
                    },
                    "type": {
                        "required": False,
                        "bootstrap": True,
                        "cli_short_name": "t",
                    },
                },
            },
        }
    )


@pytest.fixture
def old_config():
    """Represent an un-migrated config with previous default values."""
    return {
        "log_config": None,
        "log_file": None,
        "log_level": "INFO",
        "configuration": {"type": "json"},
    }


@pytest.fixture
def new_config():
    """Represents a up-to-date config with all new values."""
    return {"log": {"config_file": None, "file": None, "level": "INFO"}}


class TestBgUtils(object):
    @patch("bg_utils.open")
    @patch("json.load")
    @patch("bg_utils.logging.config.dictConfig")
    def test_setup_application_logging_from_file(
        self, config_mock, json_mock, open_mock
    ):
        fake_file = Mock()
        fake_file.__exit__ = Mock()
        fake_file.__enter__ = Mock(return_value=fake_file)
        open_mock.return_value = fake_file
        fake_config = {"foo": "bar"}
        json_mock.return_value = fake_config
        app_config = Mock(log_config="/path/to/log/config")
        bg_utils.setup_application_logging(app_config, {})
        config_mock.assert_called_with({"foo": "bar"})


class TestSafeMigrate(object):
    def test_success(self, tmpdir, spec, old_config, new_config):
        old_filename = os.path.join(str(tmpdir), "config.json")
        old_config["configuration"]["file"] = old_filename
        cli_args = {"configuration": {"file": old_filename, "type": "json"}}

        with open(old_filename, "w") as f:
            f.write(json.dumps(old_config, ensure_ascii=False))

        generated_config = bg_utils.load_application_config(spec, cli_args)
        assert generated_config.log.level == "INFO"

        with open(old_filename) as f:
            new_config_value = json.load(f)

        assert new_config_value == new_config
        assert len(os.listdir(str(tmpdir))) == 2

    def test_no_change(self, tmpdir, spec, new_config):
        config_file = os.path.join(str(tmpdir), "config.yaml")
        cli_args = {"configuration": {"file": config_file}}

        with open(config_file, "w") as f:
            yaml.safe_dump(new_config, f, default_flow_style=False, encoding="utf-8")

        generated_config = bg_utils.load_application_config(spec, cli_args)
        assert generated_config.log.level == "INFO"

        with open(config_file) as f:
            new_config_value = yaml.safe_load(f)

        assert new_config_value == new_config
        assert len(os.listdir(str(tmpdir))) == 1

    def test_migration_failure(self, capsys, tmpdir, spec, old_config):
        old_filename = os.path.join(str(tmpdir), "config.json")
        cli_args = {"configuration": {"file": old_filename, "type": "json"}}

        spec.migrate_config_file = Mock(side_effect=ValueError)

        with open(old_filename, "w") as f:
            f.write(json.dumps(old_config, ensure_ascii=False))

        generated_config = bg_utils.load_application_config(spec, cli_args)

        # Make sure we printed something
        assert capsys.readouterr().err

        # If the migration fails, we should still have a single unchanged JSON file.
        assert len(os.listdir(str(tmpdir))) == 1
        with open(old_filename) as f:
            new_config_value = json.load(f)
        assert new_config_value == old_config

        # And the values should be unchanged
        assert generated_config.log.level == "INFO"

    def test_rename_failure(self, capsys, tmpdir, spec, old_config):
        old_filename = os.path.join(str(tmpdir), "config.json")
        cli_args = {"configuration": {"file": old_filename, "type": "json"}}

        with open(old_filename, "w") as f:
            f.write(json.dumps(old_config, ensure_ascii=False))

        with patch("os.rename", Mock(side_effect=ValueError)):
            generated_config = bg_utils.load_application_config(spec, cli_args)

        # Make sure we printed something
        assert capsys.readouterr().err

        assert generated_config.log.level == "INFO"

        # Both the tmp file and the old JSON should still be there.
        assert len(os.listdir(str(tmpdir))) == 2
        with open(old_filename + ".tmp") as f:
            yaml.safe_load(f)

        # The loaded config should be the JSON file.
        with open(old_filename) as f:
            new_config_value = json.load(f)

        assert new_config_value == old_config

    def test_catastrophe(self, capsys, tmpdir, spec, old_config):
        old_filename = os.path.join(str(tmpdir), "config.json")
        cli_args = {"configuration": {"file": old_filename, "type": "json"}}

        with open(old_filename, "w") as f:
            f.write(json.dumps(old_config, ensure_ascii=False))

        with patch("os.rename", Mock(side_effect=[Mock(), ValueError])):
            with pytest.raises(ValueError):
                bg_utils.load_application_config(spec, cli_args)

        # Make sure we printed something
        assert capsys.readouterr().err

        # Both the tmp file and the old JSON should still be there.
        assert len(os.listdir(str(tmpdir))) == 2
