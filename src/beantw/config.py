"""Configuration management for beancount-taiwan importers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AccountConfig:
    """Account configuration for an importer."""

    credit_card: str
    expense: str
    payment_asset: str


@dataclass
class Rule:
    """Rule for matching and applying account overrides."""

    name: str | None = None
    type: str | None = None
    description_contains: str | None = None
    expense_account: str | None = None
    payment_asset_account: str | None = None

    def matches(self, transaction: dict[str, Any]) -> bool:
        """Check if this rule matches the given transaction.

        Args:
            transaction: Transaction data dictionary

        Returns:
            True if the rule matches, False otherwise
        """
        # Check type matching
        if self.type == "payment":
            ntd_amount = float(transaction.get("ntdAmount", 0))
            if ntd_amount >= 0:
                return False

        # Check description matching
        if self.description_contains:
            description = transaction.get("description", "")
            if self.description_contains not in description:
                return False

        return True

    def apply_to_accounts(
        self, expense_account: str, payment_asset_account: str
    ) -> tuple[str, str]:
        """Apply this rule to the given accounts.

        Args:
            expense_account: Current expense account
            payment_asset_account: Current payment asset account

        Returns:
            Tuple of (expense_account, payment_asset_account) after applying rule
        """
        if self.expense_account:
            expense_account = self.expense_account
        if self.payment_asset_account:
            payment_asset_account = self.payment_asset_account

        return expense_account, payment_asset_account


@dataclass
class CardConfig:
    """Configuration for a specific credit card."""

    name: str
    card_no_suffix: str
    accounts: AccountConfig
    rules: list[Rule]


class HSBCCreditCardConfig:
    """Configuration for HSBC credit card importer."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to YAML configuration file, or None for defaults
        """
        self.default_accounts = AccountConfig(
            credit_card="Liabilities:CreditCard:HSBC:Travelers",
            expense="Expenses:Life",
            payment_asset="Assets:Bank:Checking",
        )
        self.rules: list[Rule] = []
        self.cards: list[CardConfig] = []

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
        if "default" in config and "account" in config["default"]:
            accounts = config["default"]["account"]
            if "credit_card" in accounts:
                self.default_accounts.credit_card = accounts["credit_card"]
            if "expense" in accounts:
                self.default_accounts.expense = accounts["expense"]
            if "payment_asset" in accounts:
                self.default_accounts.payment_asset = accounts["payment_asset"]

        # Load global rules
        if "rules" in config:
            for rule_data in config["rules"]:
                rule = Rule(
                    name=rule_data.get("name"),
                    type=rule_data.get("type"),
                    description_contains=rule_data.get("description_contains"),
                    expense_account=rule_data.get("expense_account"),
                    payment_asset_account=rule_data.get("payment_asset_account"),
                )
                self.rules.append(rule)

        # Load card-specific configurations
        if "cards" in config:
            for card_data in config["cards"]:
                card_accounts_data = card_data.get("accounts", {})
                card_accounts = AccountConfig(
                    credit_card=card_accounts_data.get(
                        "credit_card", self.default_accounts.credit_card
                    ),
                    expense=card_accounts_data.get(
                        "expense", self.default_accounts.expense
                    ),
                    payment_asset=card_accounts_data.get(
                        "payment_asset", self.default_accounts.payment_asset
                    ),
                )

                card_rules = []
                if "rules" in card_data:
                    for rule_data in card_data["rules"]:
                        rule = Rule(
                            name=rule_data.get("name"),
                            type=rule_data.get("type"),
                            description_contains=rule_data.get("description_contains"),
                            expense_account=rule_data.get("expense_account"),
                            payment_asset_account=rule_data.get(
                                "payment_asset_account"
                            ),
                        )
                        card_rules.append(rule)

                card = CardConfig(
                    name=card_data["name"],
                    card_no_suffix=card_data["card_no_suffix"],
                    accounts=card_accounts,
                    rules=card_rules,
                )
                self.cards.append(card)

    def get_accounts_for_transaction(
        self, transaction: dict[str, Any]
    ) -> tuple[str, str, str]:
        """Get accounts for a transaction based on configuration.

        Args:
            transaction: Transaction data dictionary

        Returns:
            Tuple of (credit_card_account, expense_account, payment_asset_account)
        """
        # Start with default accounts
        credit_card = self.default_accounts.credit_card
        expense = self.default_accounts.expense
        payment_asset = self.default_accounts.payment_asset

        # Check if transaction matches a card configuration
        card_no = transaction.get("cardNo", "")
        for card in self.cards:
            if card_no.endswith(card.card_no_suffix):
                credit_card = card.accounts.credit_card
                expense = card.accounts.expense
                payment_asset = card.accounts.payment_asset

                # Apply card-specific rules
                for rule in card.rules:
                    if rule.matches(transaction):
                        expense, payment_asset = rule.apply_to_accounts(
                            expense, payment_asset
                        )
                        break

                return credit_card, expense, payment_asset

        # Apply global rules if no card-specific configuration matched
        for rule in self.rules:
            if rule.matches(transaction):
                expense, payment_asset = rule.apply_to_accounts(expense, payment_asset)
                break

        return credit_card, expense, payment_asset
