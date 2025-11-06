"""Tests for HSBC credit card importer."""

import json
import tempfile
from pathlib import Path

import pytest
from beancount.core import data
from beancount.core.amount import Amount
from beancount.parser import printer
from beancount.loader import load_string
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

    # Expense posting with foreign currency and per-unit price
    expense_posting = entry.postings[0]
    assert expense_posting.account == "Expenses:Life"
    assert expense_posting.units == Amount(Decimal("20.00"), "USD")
    # Per-unit price should be 600 / 20 = 30 TWD per USD
    assert expense_posting.cost is None
    assert expense_posting.price == Amount(Decimal("30"), "TWD")

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


def test_import_hsbc_credit_card_foreign_currency_refund(importer, temp_json_file):
    """Test importing a foreign currency refund (negative amount)."""
    # Given a foreign currency refund transaction with negative ntdAmount
    statement = {
        "payload": [
            {
                "amount": "20",
                "description": "REFUND FROM FOREIGN MERCHANT",
                "amtCy": "USD",
                "txnLoc": "USA",
                "txnDate": "2025/08/10",
                "cyCnvDate": "2025/08/11",
                "postingDate": "2025/08/12",
                "ntdAmount": "-600",  # Negative amount = refund
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

    # Then the output should contain Beancount entries with foreign currency handling
    assert len(entries) == 1
    entry = entries[0]

    assert isinstance(entry, data.Transaction)
    assert entry.narration == "REFUND FROM FOREIGN MERCHANT"

    # Check postings - should still use foreign currency with per-unit price
    assert len(entry.postings) == 2

    # Expense posting with foreign currency and per-unit price
    # Note: The foreign amount from HSBC is always positive (20 USD)
    # But the per-unit price will be negative because ntdAmount is negative
    expense_posting = entry.postings[0]
    assert expense_posting.account == "Expenses:Life"
    assert expense_posting.units == Amount(Decimal("20.00"), "USD")
    # Per-unit price should be -600 / 20 = -30 TWD per USD (negative for refund)
    assert expense_posting.cost is None
    assert expense_posting.price == Amount(Decimal("-30"), "TWD")

    # Credit card posting (balancing)
    cc_posting = entry.postings[1]
    assert cc_posting.account == "Liabilities:CreditCard:HSBC:Travelers"
    assert cc_posting.units is None  # Balancing posting


def test_import_hsbc_jpy_rounding_scenario(importer, temp_json_file):
    """Test importing JPY transaction with non-terminating decimal per-unit price.

    This test verifies that the per-unit price calculation handles rounding
    correctly for cases like 5500 JPY / 1136 TWD where the per-unit price
    is a non-terminating decimal (0.2065454545...).
    """
    # Given a foreign currency transaction with JPY
    statement = {
        "payload": [
            {
                "amount": "5500",
                "description": "JPY TRANSACTION WITH ROUNDING",
                "amtCy": "JPY",
                "txnLoc": "Japan",
                "txnDate": "2025/08/01",
                "cyCnvDate": "2025/08/02",
                "postingDate": "2025/08/03",
                "ntdAmount": "1136",
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

    # Then the output should contain a properly balanced transaction
    assert len(entries) == 1
    entry = entries[0]

    assert isinstance(entry, data.Transaction)
    assert entry.narration == "JPY TRANSACTION WITH ROUNDING"

    # Check postings
    assert len(entry.postings) == 2

    # Expense posting with JPY and per-unit price
    expense_posting = entry.postings[0]
    assert expense_posting.account == "Expenses:Life"
    assert expense_posting.units == Amount(Decimal("5500"), "JPY")
    assert expense_posting.cost is None

    # Per-unit price should be 1136 / 5500 = 0.2065454545...
    expected_per_unit_price = Decimal("1136") / Decimal("5500")
    assert expense_posting.price == Amount(expected_per_unit_price, "TWD")

    # Verify the calculated total matches the original TWD amount
    # When Beancount calculates: 5500 JPY @ (1136/5500) TWD
    # The result should balance to exactly 1136 TWD
    calculated_total = expense_posting.units.number * expense_posting.price.number
    assert calculated_total == Decimal("1136")

    # Credit card posting (balancing)
    cc_posting = entry.postings[1]
    assert cc_posting.account == "Liabilities:CreditCard:HSBC:Travelers"
    assert cc_posting.units is None  # Balancing posting

    # Verify Beancount can properly balance this transaction
    # Print the transaction to verify the format
    txn_text = printer.format_entry(entry)
    print(f"\nGenerated transaction:\n{txn_text}")

    # Test that we can load this transaction with Beancount's parser
    # This is the definitive test - if Beancount can parse and validate it, it's correct
    beancount_file_content = f"""
option "operating_currency" "TWD"

2020-01-01 open Expenses:Life
2020-01-01 open Liabilities:CreditCard:HSBC:Travelers

{txn_text}
"""
    # Load and validate using Beancount's loader
    loaded_entries, errors, options = load_string(beancount_file_content)

    # Check there are no errors
    assert len(errors) == 0, (
        f"Beancount failed to parse/validate JPY rounding scenario. "
        f"Errors: {errors}\n"
        f"Content:\n{beancount_file_content}"
    )

    # Verify we got the transaction (plus 2 open directives)
    assert len(loaded_entries) == 3, f"Expected 3 entries, got {len(loaded_entries)}"
