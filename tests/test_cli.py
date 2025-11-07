"""Tests for CLI functionality."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from beantw.cli import app

runner = CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_statement():
    """Create a sample HSBC statement data."""
    return {
        "payload": [
            {
                "amount": "0",
                "description": "TEST TRANSACTION",
                "amtCy": "",
                "txnLoc": "",
                "txnDate": "2025/07/29",
                "cyCnvDate": "",
                "postingDate": "2025/08/04",
                "ntdAmount": "699",
                "isForeignTxn": False,
                "isInstallmentTxn": False,
                "cardNo": "1234",
                "relationShip": "P",
            }
        ]
    }


def test_convert_without_config(temp_dir, sample_statement):
    """Test convert command works without a config file."""
    # Create statement file
    statement_file = temp_dir / "statement.json"
    with open(statement_file, "w") as f:
        json.dump(sample_statement, f)

    # Run convert command without config
    result = runner.invoke(app, [str(statement_file)])

    # Should succeed and use default accounts
    assert result.exit_code == 0
    assert "TEST TRANSACTION" in result.stdout
    assert "Expenses:Others" in result.stdout  # New default
    assert "Liabilities:CreditCard:HSBC:Travelers" in result.stdout


def test_convert_with_explicit_config(temp_dir, sample_statement):
    """Test convert command with explicitly specified config file."""
    # Create config file with new simplified format
    config_data = {
        "default": {
            "source": "Liabilities:CustomCard",
            "target": "Expenses:Custom",
        }
    }
    config_file = temp_dir / "custom_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Create statement file
    statement_file = temp_dir / "statement.json"
    with open(statement_file, "w") as f:
        json.dump(sample_statement, f)

    # Run convert command with explicit config
    result = runner.invoke(app, ["--config", str(config_file), str(statement_file)])

    # Should use config file accounts
    assert result.exit_code == 0
    assert "TEST TRANSACTION" in result.stdout
    assert "Expenses:Custom" in result.stdout
    assert "Liabilities:CustomCard" in result.stdout


def test_convert_with_default_config_in_config_dir(temp_dir, sample_statement):
    """Test that convert command automatically detects config/hsbc_credit_card_importer.yaml."""
    # Change to temp directory
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)

        # Create config directory and default config file
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        config_data = {
            "default": {
                "source": "Liabilities:AutoDetected",
                "target": "Expenses:AutoDetected",
            }
        }
        config_file = config_dir / "hsbc_credit_card_importer.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create statement file
        statement_file = temp_dir / "statement.json"
        with open(statement_file, "w") as f:
            json.dump(sample_statement, f)

        # Run convert command without specifying config (should auto-detect)
        result = runner.invoke(app, [str(statement_file)])

        # Should automatically use the config file
        assert result.exit_code == 0
        assert "TEST TRANSACTION" in result.stdout
        assert "Expenses:AutoDetected" in result.stdout
        assert "Liabilities:AutoDetected" in result.stdout

    finally:
        os.chdir(original_cwd)


def test_explicit_config_overrides_default(temp_dir, sample_statement):
    """Test that explicit config file overrides default config location."""
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)

        # Create default config
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        default_config_data = {
            "default": {
                "source": "Liabilities:Default",
                "target": "Expenses:Default",
            }
        }
        default_config_file = config_dir / "hsbc_credit_card_importer.yaml"
        with open(default_config_file, "w") as f:
            yaml.dump(default_config_data, f)

        # Create explicit config
        explicit_config_data = {
            "default": {
                "source": "Liabilities:Explicit",
                "target": "Expenses:Explicit",
            }
        }
        explicit_config_file = temp_dir / "explicit.yaml"
        with open(explicit_config_file, "w") as f:
            yaml.dump(explicit_config_data, f)

        # Create statement file
        statement_file = temp_dir / "statement.json"
        with open(statement_file, "w") as f:
            json.dump(sample_statement, f)

        # Run with explicit config
        result = runner.invoke(
            app, ["--config", str(explicit_config_file), str(statement_file)]
        )

        # Should use explicit config, not default
        assert result.exit_code == 0
        assert "Expenses:Explicit" in result.stdout
        assert "Expenses:Default" not in result.stdout

    finally:
        os.chdir(original_cwd)


def test_cli_options_override_config(temp_dir, sample_statement):
    """Test that CLI options override config file settings."""
    # Create config file
    config_data = {
        "default": {
            "source": "Liabilities:FromConfig",
            "target": "Expenses:FromConfig",
        }
    }
    config_file = temp_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Create statement file
    statement_file = temp_dir / "statement.json"
    with open(statement_file, "w") as f:
        json.dump(sample_statement, f)

    # Run with config but override target account
    result = runner.invoke(
        app,
        [
            "--config",
            str(config_file),
            "--target-account",
            "Expenses:OverriddenCLI",
            str(statement_file),
        ],
    )

    # Should use CLI option for target, config for source
    assert result.exit_code == 0
    assert "Expenses:OverriddenCLI" in result.stdout
    assert "Expenses:FromConfig" not in result.stdout
    assert "Liabilities:FromConfig" in result.stdout
