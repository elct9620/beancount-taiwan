"""Configuration management for beancount-taiwan importers."""

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class RecurringFrequency(str, Enum):
    """Enum for recurring transaction frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class Category:
    """Category rule for matching transactions by description pattern."""

    pattern: str  # Regex pattern
    account: str  # Account to use for matching transactions


class HSBCCreditCardConfig:
    """Configuration for HSBC credit card importer.

    Simplified configuration structure:
    - source: The credit card liability account
    - target: The default expense account for regular transactions
    - categories: Pattern-based rules for special transaction types
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to YAML configuration file, or None for defaults
        """
        # Default accounts
        self.source_account = "Liabilities:CreditCard:HSBC:Travelers"
        self.target_account = "Expenses:Others"
        self.categories: list[Category] = []

        if config_path:
            self._load_config(config_path)

    def _load_config(self, config_path: str | Path) -> None:
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file
        """
        path = Path(config_path)
        if not path.exists():
            raise ValueError(f"Configuration file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            return

        # Load default accounts
        if "default" in config:
            if "source" in config["default"]:
                self.source_account = config["default"]["source"]
            if "target" in config["default"]:
                self.target_account = config["default"]["target"]

        # Load categories
        if "categories" in config:
            for cat_data in config["categories"]:
                category = Category(
                    pattern=cat_data["pattern"], account=cat_data["account"]
                )
                self.categories.append(category)

    def get_account_for_transaction(self, transaction: dict[str, Any]) -> str:
        """Get the account for a transaction based on description pattern matching.

        Args:
            transaction: Transaction data dictionary

        Returns:
            Account name (either a category-matched account or target account)
        """
        description = transaction.get("description", "")

        # Check categories in order
        for category in self.categories:
            if re.match(category.pattern, description):
                return category.account

        # Return default target account
        return self.target_account


@dataclass
class RecurringTransaction:
    """Definition of a recurring transaction."""

    description: str
    amount: float
    currency: str
    source_account: str
    target_account: str
    frequency: RecurringFrequency
    start_date: date
    book: str  # Template path for the Beancount file


class RecurringTransactionConfig:
    """Configuration for recurring transactions.

    The configuration defines recurring transactions that should be
    automatically added to Beancount files.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to YAML configuration file, or None for defaults
        """
        self.recurring_transactions: list[RecurringTransaction] = []

        if config_path:
            self._load_config(config_path)

    def _load_config(self, config_path: str | Path) -> None:
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file
        """
        path = Path(config_path)
        if not path.exists():
            raise ValueError(f"Configuration file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config or "recurring_transactions" not in config:
            return

        # Load recurring transactions
        for txn_data in config["recurring_transactions"]:
            # Parse the start_date string to a date object
            start_date_str = txn_data["start_date"]
            if isinstance(start_date_str, str):
                start_date = date.fromisoformat(start_date_str)
            else:
                start_date = start_date_str

            # Parse frequency string to enum
            frequency_str = txn_data["frequency"]
            try:
                frequency = RecurringFrequency(frequency_str.lower())
            except ValueError:
                valid_frequencies = ", ".join([f.value for f in RecurringFrequency])
                raise ValueError(
                    f"Invalid frequency '{frequency_str}'. Must be one of: {valid_frequencies}"
                )

            transaction = RecurringTransaction(
                description=txn_data["description"],
                amount=txn_data["amount"],
                currency=txn_data["currency"],
                source_account=txn_data["source_account"],
                target_account=txn_data["target_account"],
                frequency=frequency,
                start_date=start_date,
                book=txn_data["book"],
            )
            self.recurring_transactions.append(transaction)
