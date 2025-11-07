"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from beantw.config import HSBCCreditCardConfig, Category


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file and clean it up after test."""
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yield temp_file
    temp_file.close()
    Path(temp_file.name).unlink(missing_ok=True)


def test_load_default_accounts_from_config(temp_yaml_file):
    """Test loading default account configuration from YAML."""
    # Given a config file with default accounts
    config_data = {
        "default": {
            "source": "Liabilities:CreditCard:HSBC:Custom",
            "target": "Expenses:Custom",
        }
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    # When loading the configuration
    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # Then the default accounts should be loaded
    assert config.source_account == "Liabilities:CreditCard:HSBC:Custom"
    assert config.target_account == "Expenses:Custom"


def test_load_categories_from_config(temp_yaml_file):
    """Test loading categories from configuration."""
    # Given a config file with categories
    config_data = {
        "categories": [
            {
                "pattern": "^PAYMENT RECEIVED$",
                "account": "Assets:Bank:Checking",
            },
            {
                "pattern": "^國外交易手續費$",
                "account": "Expenses:BankFees",
            },
        ]
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    # When loading the configuration
    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # Then the categories should be loaded
    assert len(config.categories) == 2
    assert config.categories[0].pattern == "^PAYMENT RECEIVED$"
    assert config.categories[0].account == "Assets:Bank:Checking"
    assert config.categories[1].pattern == "^國外交易手續費$"
    assert config.categories[1].account == "Expenses:BankFees"


def test_get_account_for_transaction_with_category_match(temp_yaml_file):
    """Test getting account for a transaction using category matching."""
    # Given a config with categories
    config_data = {
        "default": {
            "source": "Liabilities:CreditCard:HSBC:Travelers",
            "target": "Expenses:Others",
        },
        "categories": [
            {
                "pattern": "^PAYMENT RECEIVED$",
                "account": "Assets:Bank:Checking",
            },
            {
                "pattern": "^國外交易手續費$",
                "account": "Expenses:BankFees",
            },
        ],
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # When getting account for a transaction matching a category
    transaction = {"description": "PAYMENT RECEIVED"}
    account = config.get_account_for_transaction(transaction)

    # Then the category-matched account should be returned
    assert account == "Assets:Bank:Checking"


def test_get_account_for_transaction_without_match(temp_yaml_file):
    """Test getting account for a transaction that doesn't match any category."""
    # Given a config with categories
    config_data = {
        "default": {
            "source": "Liabilities:CreditCard:HSBC:Travelers",
            "target": "Expenses:Others",
        },
        "categories": [
            {
                "pattern": "^PAYMENT RECEIVED$",
                "account": "Assets:Bank:Checking",
            },
        ],
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # When getting account for a transaction that doesn't match
    transaction = {"description": "REGULAR EXPENSE"}
    account = config.get_account_for_transaction(transaction)

    # Then the default target account should be returned
    assert account == "Expenses:Others"


def test_category_pattern_matching():
    """Test that category patterns match correctly using regex."""
    # Given a config with a regex pattern
    config = HSBCCreditCardConfig()
    config.categories.append(
        Category(pattern="^國外交易手續費", account="Expenses:BankFees")
    )

    # When checking a matching transaction
    transaction = {"description": "國外交易手續費 2025/07/30"}
    account = config.get_account_for_transaction(transaction)

    # Then it should match
    assert account == "Expenses:BankFees"


def test_category_first_match_wins():
    """Test that the first matching category is used."""
    # Given a config with overlapping patterns
    config = HSBCCreditCardConfig()
    config.categories.append(Category(pattern="^PAYMENT", account="Assets:Bank:First"))
    config.categories.append(
        Category(pattern="^PAYMENT RECEIVED$", account="Assets:Bank:Second")
    )

    # When getting account for a transaction
    transaction = {"description": "PAYMENT RECEIVED"}
    account = config.get_account_for_transaction(transaction)

    # Then the first matching category should be used
    assert account == "Assets:Bank:First"


def test_config_file_not_found_raises_error():
    """Test that loading a non-existent config file raises an error."""
    # When loading a non-existent config file
    with pytest.raises(ValueError, match="Configuration file not found"):
        HSBCCreditCardConfig("/nonexistent/config.yaml")


def test_default_config_without_file():
    """Test that default configuration is used when no file is provided."""
    # When creating a config without a file
    config = HSBCCreditCardConfig()

    # Then default accounts should be used
    assert config.source_account == "Liabilities:CreditCard:HSBC:Travelers"
    assert config.target_account == "Expenses:Others"
    assert len(config.categories) == 0
