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
    result = runner.invoke(app, ["convert", str(statement_file)])

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
    result = runner.invoke(
        app, ["convert", "--config", str(config_file), str(statement_file)]
    )

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
        result = runner.invoke(app, ["convert", str(statement_file)])

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
            app, ["convert", "--config", str(explicit_config_file), str(statement_file)]
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
            "convert",
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


def test_refresh_command(temp_dir):
    """Test refresh command creates index files."""
    # Create directory structure with beancount files
    books_dir = temp_dir / "books"
    (books_dir / "2023").mkdir(parents=True)
    (books_dir / "2024").mkdir(parents=True)

    # Create beancount files
    (books_dir / "2023" / "jan.bean").write_text(
        '2023-01-01 * "Test"\n  Assets:Cash 100 TWD\n'
    )
    (books_dir / "2023" / "feb.bean").write_text(
        '2023-02-01 * "Test"\n  Assets:Cash 200 TWD\n'
    )
    (books_dir / "2024" / "mar.bean").write_text(
        '2024-03-01 * "Test"\n  Assets:Cash 300 TWD\n'
    )

    # Run refresh command
    result = runner.invoke(app, ["refresh", str(books_dir)])

    # Should succeed
    assert result.exit_code == 0
    assert "Successfully refreshed" in result.stdout

    # Verify index files were created
    assert (books_dir / "2023" / "index.bean").exists()
    assert (books_dir / "2024" / "index.bean").exists()
    assert (books_dir / "index.bean").exists()

    # Verify content
    content_2023 = (books_dir / "2023" / "index.bean").read_text()
    assert 'include "feb.bean"' in content_2023
    assert 'include "jan.bean"' in content_2023


def test_refresh_command_with_default_directory(temp_dir):
    """Test refresh command with default directory argument."""
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)

        # Create default books directory
        books_dir = temp_dir / "books"
        books_dir.mkdir()
        (books_dir / "test.bean").write_text(
            '2023-01-01 * "Test"\n  Assets:Cash 100 TWD\n'
        )

        # Run refresh without directory argument (should use default "books")
        result = runner.invoke(app, ["refresh"])

        # Should succeed
        assert result.exit_code == 0
        assert "Successfully refreshed" in result.stdout

        # Verify index file was created
        assert (books_dir / "index.bean").exists()

    finally:
        os.chdir(original_cwd)
