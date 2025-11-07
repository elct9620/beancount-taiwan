"""Configuration management for beancount-taiwan importers."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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
