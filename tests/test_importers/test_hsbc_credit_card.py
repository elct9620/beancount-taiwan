"""Tests for HSBC credit card importer."""

import json
import tempfile
from pathlib import Path

import pytest
from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.position import Cost
from decimal import Decimal

from beantw.config import HSBCCreditCardConfig, Rule
from beantw.importers.hsbc_credit_card import HSBCCreditCardImporter


@pytest.fixture
def importer():
    """Create an HSBC credit card importer with default configuration."""
    return HSBCCreditCardImporter(
        credit_card_account="Liabilities:CreditCard:HSBC:Travelers",
        expense_account="Expenses:Life",
        payment_asset_account="Assets:Bank:Checking",
    )


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file and clean it up after test."""
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    yield temp_file
    temp_file.close()
    Path(temp_file.name).unlink(missing_ok=True)


def test_import_hsbc_credit_card_expense(importer, temp_json_file):
    """Test importing a regular expense transaction."""
    # Given a valid HSBC credit card statement payload
    statement = {
        "payload": [
            {
                "amount": "0",
                "description": "TEST TRANSACTION 1",
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

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When I extract entries from the file
    entries = importer.extract(temp_json_file.name)

    # Then the output should contain Beancount entries
    assert len(entries) == 1
    entry = entries[0]

    assert isinstance(entry, data.Transaction)
    assert entry.date.year == 2025
    assert entry.date.month == 8
    assert entry.date.day == 4
    assert entry.narration == "TEST TRANSACTION 1"
    assert entry.meta.get("cardNo") == "1234"
    assert entry.meta.get("tnxDate") == "2025-07-29"

    # Check postings
    assert len(entry.postings) == 2

    # Expense posting
    expense_posting = entry.postings[0]
    assert expense_posting.account == "Expenses:Life"
    assert expense_posting.units == Amount(Decimal("699.00"), "TWD")

    # Credit card posting
    cc_posting = entry.postings[1]
    assert cc_posting.account == "Liabilities:CreditCard:HSBC:Travelers"
    assert cc_posting.units is None  # Balancing posting


def test_import_hsbc_credit_card_foreign_currency_expense(importer, temp_json_file):
    """Test importing a foreign currency expense transaction."""
    # Given a valid HSBC credit card statement payload with foreign currency
    statement = {
        "payload": [
            {
                "amount": "20",
                "description": "FOREIGN TRANSACTION",
                "amtCy": "USD",
                "txnLoc": "USA",
                "txnDate": "2025/07/30",
                "cyCnvDate": "2025/08/01",
                "postingDate": "2025/08/05",
                "ntdAmount": "600",
                "isForeignTxn": True,
                "isInstallmentTxn": False,
                "cardNo": "1234",
                "relationShip": "",
            }
        ]
    }

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When I extract entries from the file
    entries = importer.extract(temp_json_file.name)

    # Then the output should contain Beancount entries with price conversion
    assert len(entries) == 1
    entry = entries[0]

    assert isinstance(entry, data.Transaction)
    assert entry.date.year == 2025
    assert entry.date.month == 8
    assert entry.date.day == 5
    assert entry.narration == "FOREIGN TRANSACTION"
    assert entry.meta.get("cardNo") == "1234"
    assert entry.meta.get("tnxDate") == "2025-07-30"
    assert entry.meta.get("tnxLoc") == "USA"

    # Check postings
    assert len(entry.postings) == 2

    # Expense posting with foreign currency and total cost
    expense_posting = entry.postings[0]
    assert expense_posting.account == "Expenses:Life"
    assert expense_posting.units == Amount(Decimal("20.00"), "USD")
    assert expense_posting.cost == Cost(Decimal("600.00"), "TWD", None, None)

    # Credit card posting
    cc_posting = entry.postings[1]
    assert cc_posting.account == "Liabilities:CreditCard:HSBC:Travelers"


def test_import_hsbc_credit_card_payment(importer, temp_json_file):
    """Test importing a payment transaction."""
    # Given a valid HSBC credit card statement payload with payment
    statement = {
        "payload": [
            {
                "amount": "0",
                "description": "PAYMENT RECEIVED",
                "amtCy": "",
                "txnLoc": "",
                "txnDate": "2025/07/31",
                "cyCnvDate": "",
                "postingDate": "2025/08/06",
                "ntdAmount": "-5000",
                "isForeignTxn": False,
                "isInstallmentTxn": False,
                "cardNo": "1234",
                "relationShip": "",
            }
        ]
    }

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When I extract entries from the file
    entries = importer.extract(temp_json_file.name)

    # Then the output should contain payment entries
    assert len(entries) == 1
    entry = entries[0]

    assert isinstance(entry, data.Transaction)
    assert entry.narration == "PAYMENT RECEIVED"

    # Check postings for payment (negative amount reduces liability)
    assert len(entry.postings) == 2

    cc_posting = entry.postings[0]
    assert cc_posting.account == "Liabilities:CreditCard:HSBC:Travelers"
    assert cc_posting.units == Amount(Decimal("-5000.00"), "TWD")

    asset_posting = entry.postings[1]
    assert asset_posting.account == "Assets:Bank:Checking"


def test_import_hsbc_credit_card_foreign_transaction_fee(importer, temp_json_file):
    """Test importing a foreign transaction fee."""
    # Given a valid HSBC credit card statement with foreign transaction fee
    statement = {
        "payload": [
            {
                "amount": "0",
                "description": "國外交易手續費",
                "amtCy": "   ",
                "txnLoc": "",
                "txnDate": "2025/09/03",
                "cyCnvDate": "",
                "postingDate": "2025/09/04",
                "ntdAmount": "39",
                "isForeignTxn": False,
                "isInstallmentTxn": False,
                "cardNo": "",
                "relationShip": "",
            }
        ]
    }

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When I extract entries from the file
    entries = importer.extract(temp_json_file.name)

    # Then the output should contain fee entries
    assert len(entries) == 1
    entry = entries[0]

    assert isinstance(entry, data.Transaction)
    assert entry.narration == "國外交易手續費"
    assert entry.meta.get("tnxDate") == "2025-09-03"

    # Note: cardNo might be empty for fees, so we shouldn't check it


def test_handle_invalid_json_file(importer, temp_json_file):
    """Test error handling for invalid JSON structure."""
    # Given an invalid HSBC credit card statement payload
    invalid_statement = {"invalid_key": []}

    json.dump(invalid_statement, temp_json_file)
    temp_json_file.flush()

    # When/Then it should raise an error
    with pytest.raises(ValueError, match="not a valid HSBC credit card statement"):
        importer.extract(temp_json_file.name)


def test_identify_hsbc_credit_card_file(importer, temp_json_file):
    """Test file identification for HSBC credit card JSON files."""
    # Given a valid HSBC credit card statement file
    statement = {
        "payload": [
            {
                "amount": "0",
                "description": "TEST",
                "txnDate": "2025/07/29",
                "postingDate": "2025/08/04",
                "ntdAmount": "100",
                "cardNo": "1234",
            }
        ]
    }

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When I identify the file
    result = importer.identify(temp_json_file.name)

    # Then it should be identified correctly
    assert result is True


def test_reject_non_hsbc_file(importer, temp_json_file):
    """Test that non-HSBC files are rejected."""
    # Given a file with different structure
    other_file = {"data": []}

    json.dump(other_file, temp_json_file)
    temp_json_file.flush()

    # When I identify the file
    result = importer.identify(temp_json_file.name)

    # Then it should not be identified
    assert result is False


def test_multiple_transactions(importer, temp_json_file):
    """Test importing multiple transactions from one file."""
    # Given multiple transactions in the payload
    statement = {
        "payload": [
            {
                "amount": "0",
                "description": "TRANSACTION 1",
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
            },
            {
                "amount": "0",
                "description": "TRANSACTION 2",
                "amtCy": "",
                "txnLoc": "",
                "txnDate": "2025/07/30",
                "cyCnvDate": "",
                "postingDate": "2025/08/05",
                "ntdAmount": "500",
                "isForeignTxn": False,
                "isInstallmentTxn": False,
                "cardNo": "1234",
                "relationShip": "P",
            },
        ]
    }

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When I extract entries
    entries = importer.extract(temp_json_file.name)

    # Then I should get multiple entries
    assert len(entries) == 2
    assert entries[0].narration == "TRANSACTION 1"
    assert entries[1].narration == "TRANSACTION 2"


def test_import_with_config_rule_matching(temp_json_file):
    """Test that importer applies configuration rules correctly."""
    # Given a config with a rule for foreign transaction fees
    config = HSBCCreditCardConfig()
    config.rules.append(
        Rule(description_contains="國外交易手續費", expense_account="Expenses:BankFees")
    )

    # And an importer using this config
    importer = HSBCCreditCardImporter(config=config)

    # And a transaction matching the rule
    statement = {
        "payload": [
            {
                "amount": "0",
                "description": "國外交易手續費",
                "amtCy": "   ",
                "txnLoc": "",
                "txnDate": "2025/09/03",
                "cyCnvDate": "",
                "postingDate": "2025/09/04",
                "ntdAmount": "39",
                "isForeignTxn": False,
                "isInstallmentTxn": False,
                "cardNo": "",
                "relationShip": "",
            }
        ]
    }

    json.dump(statement, temp_json_file)
    temp_json_file.flush()

    # When extracting entries
    entries = importer.extract(temp_json_file.name)

    # Then the rule should apply the BankFees account
    assert len(entries) == 1
    entry = entries[0]
    expense_posting = entry.postings[0]
    assert expense_posting.account == "Expenses:BankFees"
