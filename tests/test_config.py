"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from beantw.config import HSBCCreditCardConfig, Rule


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
            "account": {
                "credit_card": "Liabilities:CreditCard:HSBC:Custom",
                "expense": "Expenses:Custom",
                "payment_asset": "Assets:Custom",
            }
        }
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    # When loading the configuration
    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # Then the default accounts should be loaded
    assert config.default_accounts.credit_card == "Liabilities:CreditCard:HSBC:Custom"
    assert config.default_accounts.expense == "Expenses:Custom"
    assert config.default_accounts.payment_asset == "Assets:Custom"


def test_load_global_rules_from_config(temp_yaml_file):
    """Test loading global rules from configuration."""
    # Given a config file with global rules
    config_data = {
        "rules": [
            {
                "name": "foreign_currency_expense",
                "description_contains": "國外交易手續費",
                "expense_account": "Expenses:BankFees",
            },
            {
                "type": "payment",
                "description_contains": "全國繳費網",
                "payment_asset_account": "Assets:Bank:PostOffice",
            },
        ]
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    # When loading the configuration
    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # Then the rules should be loaded
    assert len(config.rules) == 2
    assert config.rules[0].name == "foreign_currency_expense"
    assert config.rules[0].description_contains == "國外交易手續費"
    assert config.rules[0].expense_account == "Expenses:BankFees"
    assert config.rules[1].type == "payment"
    assert config.rules[1].payment_asset_account == "Assets:Bank:PostOffice"


def test_load_card_specific_config(temp_yaml_file):
    """Test loading card-specific configuration."""
    # Given a config file with card-specific settings
    config_data = {
        "cards": [
            {
                "name": "Travelers",
                "card_no_suffix": "1234",
                "accounts": {
                    "credit_card": "Liabilities:CreditCard:HSBC:Travelers",
                    "expense": "Expenses:Travel",
                    "payment_asset": "Assets:Bank:TravelersChecking",
                },
                "rules": [
                    {
                        "name": "foreign_currency_expense",
                        "description_contains": "FOREIGN TRANSACTION FEE",
                        "expense_account": "Expenses:BankFees",
                    }
                ],
            }
        ]
    }

    yaml.dump(config_data, temp_yaml_file)
    temp_yaml_file.flush()

    # When loading the configuration
    config = HSBCCreditCardConfig(temp_yaml_file.name)

    # Then card-specific configuration should be loaded
    assert len(config.cards) == 1
    card = config.cards[0]
    assert card.name == "Travelers"
    assert card.card_no_suffix == "1234"
    assert card.accounts.credit_card == "Liabilities:CreditCard:HSBC:Travelers"
    assert card.accounts.expense == "Expenses:Travel"
    assert len(card.rules) == 1
    assert card.rules[0].expense_account == "Expenses:BankFees"


def test_rule_matches_description():
    """Test that a rule correctly matches transaction descriptions."""
    # Given a rule that matches a specific description
    rule = Rule(description_contains="國外交易手續費")

    # When checking a matching transaction
    transaction = {"description": "國外交易手續費 2025/07/30"}

    # Then the rule should match
    assert rule.matches(transaction) is True


def test_rule_does_not_match_different_description():
    """Test that a rule doesn't match non-matching descriptions."""
    # Given a rule that matches a specific description
    rule = Rule(description_contains="國外交易手續費")

    # When checking a non-matching transaction
    transaction = {"description": "REGULAR TRANSACTION"}

    # Then the rule should not match
    assert rule.matches(transaction) is False


def test_rule_matches_payment_type():
    """Test that a rule correctly matches payment transactions."""
    # Given a rule that matches payment type
    rule = Rule(type="payment")

    # When checking a payment transaction (negative amount)
    transaction = {"ntdAmount": "-5000", "description": "PAYMENT"}

    # Then the rule should match
    assert rule.matches(transaction) is True


def test_rule_does_not_match_non_payment():
    """Test that a payment rule doesn't match expense transactions."""
    # Given a rule that matches payment type
    rule = Rule(type="payment")

    # When checking an expense transaction (positive amount)
    transaction = {"ntdAmount": "699", "description": "EXPENSE"}

    # Then the rule should not match
    assert rule.matches(transaction) is False


def test_rule_applies_expense_account_override():
    """Test that a rule applies expense account override."""
    # Given a rule that overrides the expense account
    rule = Rule(expense_account="Expenses:BankFees")

    # When applying the rule
    expense, payment = rule.apply_to_accounts("Expenses:Life", "Assets:Bank:Checking")

    # Then the expense account should be overridden
    assert expense == "Expenses:BankFees"
    assert payment == "Assets:Bank:Checking"


def test_rule_applies_payment_asset_account_override():
    """Test that a rule applies payment asset account override."""
    # Given a rule that overrides the payment asset account
    rule = Rule(payment_asset_account="Assets:Bank:PostOffice")

    # When applying the rule
    expense, payment = rule.apply_to_accounts("Expenses:Life", "Assets:Bank:Checking")

    # Then the payment asset account should be overridden
    assert expense == "Expenses:Life"
    assert payment == "Assets:Bank:PostOffice"


def test_get_accounts_for_transaction_with_global_rule():
    """Test getting accounts for a transaction using global rules."""
    # Given a config with a global rule
    config = HSBCCreditCardConfig()
    config.rules.append(
        Rule(description_contains="國外交易手續費", expense_account="Expenses:BankFees")
    )

    # When getting accounts for a matching transaction
    transaction = {"description": "國外交易手續費", "cardNo": "9999"}
    credit_card, expense, payment = config.get_accounts_for_transaction(transaction)

    # Then the rule should be applied
    assert expense == "Expenses:BankFees"


def test_get_accounts_for_transaction_with_card_specific_config():
    """Test getting accounts for a transaction using card-specific config."""
    # Given a config with card-specific settings
    config = HSBCCreditCardConfig()
    from beantw.config import AccountConfig, CardConfig

    card = CardConfig(
        name="Travelers",
        card_no_suffix="1234",
        accounts=AccountConfig(
            credit_card="Liabilities:CreditCard:HSBC:Travelers",
            expense="Expenses:Travel",
            payment_asset="Assets:Bank:TravelersChecking",
        ),
        rules=[],
    )
    config.cards.append(card)

    # When getting accounts for a transaction with matching card number
    transaction = {"description": "EXPENSE", "cardNo": "****1234"}
    credit_card, expense, payment = config.get_accounts_for_transaction(transaction)

    # Then card-specific accounts should be used
    assert credit_card == "Liabilities:CreditCard:HSBC:Travelers"
    assert expense == "Expenses:Travel"
    assert payment == "Assets:Bank:TravelersChecking"


def test_get_accounts_for_transaction_with_card_specific_rule():
    """Test that card-specific rules override card defaults."""
    # Given a config with card-specific rule
    config = HSBCCreditCardConfig()
    from beantw.config import AccountConfig, CardConfig

    card = CardConfig(
        name="Travelers",
        card_no_suffix="1234",
        accounts=AccountConfig(
            credit_card="Liabilities:CreditCard:HSBC:Travelers",
            expense="Expenses:Travel",
            payment_asset="Assets:Bank:TravelersChecking",
        ),
        rules=[
            Rule(
                description_contains="FOREIGN TRANSACTION FEE",
                expense_account="Expenses:BankFees",
            )
        ],
    )
    config.cards.append(card)

    # When getting accounts for a transaction with matching card and rule
    transaction = {"description": "FOREIGN TRANSACTION FEE", "cardNo": "****1234"}
    credit_card, expense, payment = config.get_accounts_for_transaction(transaction)

    # Then the card-specific rule should override the card default
    assert expense == "Expenses:BankFees"


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
    assert (
        config.default_accounts.credit_card == "Liabilities:CreditCard:HSBC:Travelers"
    )
    assert config.default_accounts.expense == "Expenses:Life"
    assert config.default_accounts.payment_asset == "Assets:Bank:Checking"
    assert len(config.rules) == 0
    assert len(config.cards) == 0
