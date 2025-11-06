"""HSBC Credit Card Importer using beangulp framework."""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from beancount.core import data
from beancount.core.amount import Amount
from beangulp import Importer

from beantw.config import HSBCCreditCardConfig


class HSBCCreditCardImporter(Importer):
    """Importer for HSBC credit card statement JSON files."""

    def __init__(
        self,
        credit_card_account: str | None = None,
        expense_account: str | None = None,
        payment_asset_account: str | None = None,
        config: HSBCCreditCardConfig | None = None,
    ):
        """Initialize the HSBC credit card importer.

        Args:
            credit_card_account: The Beancount account for the credit card liability
            expense_account: The default expense account for transactions
            payment_asset_account: The asset account for payment transactions
            config: Optional configuration object for advanced features like rules and card-specific configs
        """
        self.config = config

        # Store which accounts were explicitly provided (for CLI overrides)
        self._explicit_credit_card = credit_card_account
        self._explicit_expense = expense_account
        self._explicit_payment_asset = payment_asset_account

        if config:
            # Use config defaults if individual params not provided
            self.credit_card_account = (
                credit_card_account or config.default_accounts.credit_card
            )
            self.expense_account = expense_account or config.default_accounts.expense
            self.payment_asset_account = (
                payment_asset_account or config.default_accounts.payment_asset
            )
        else:
            # Use provided accounts or fall back to hardcoded defaults
            self.credit_card_account = (
                credit_card_account or "Liabilities:CreditCard:HSBC:Travelers"
            )
            self.expense_account = expense_account or "Expenses:Life"
            self.payment_asset_account = payment_asset_account or "Assets:Bank:Checking"

    def account(self, filepath: str) -> str:
        """Return the primary account for this importer.

        Args:
            filepath: Path to the file being imported

        Returns:
            The credit card account name
        """
        return self.credit_card_account

    def identify(self, filepath: str) -> bool:
        """Identify if the file is an HSBC credit card statement JSON.

        Args:
            filepath: Path to the file to identify

        Returns:
            True if the file is a valid HSBC credit card statement, False otherwise
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if it has the expected structure
            if not isinstance(data, dict):
                return False

            if "payload" not in data:
                return False

            payload = data["payload"]
            if not isinstance(payload, list):
                return False

            # If payload is empty, it's still valid
            if len(payload) == 0:
                return True

            # Check if first transaction has expected fields
            first_txn = payload[0]
            required_fields = {"description", "postingDate", "ntdAmount"}
            return required_fields.issubset(first_txn.keys())

        except (json.JSONDecodeError, IOError, KeyError):
            return False

    def extract(self, filepath: str, existing_entries=None) -> list[data.Directive]:
        """Extract transactions from HSBC credit card statement JSON.

        Args:
            filepath: Path to the JSON file
            existing_entries: Existing entries (not used)

        Returns:
            List of Beancount transaction directives

        Raises:
            ValueError: If the file is not a valid HSBC credit card statement
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                statement_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to read JSON file: {filepath}. Error: {e}") from e

        if "payload" not in statement_data:
            raise ValueError(
                f"{filepath} is not a valid HSBC credit card statement JSON file. "
                "Missing 'payload' key."
            )

        payload = statement_data["payload"]
        if not isinstance(payload, list):
            raise ValueError(
                f"{filepath} is not a valid HSBC credit card statement JSON file. "
                "'payload' must be a list."
            )

        entries = []
        for txn in payload:
            entry = self._convert_transaction(txn, filepath)
            if entry:
                entries.append(entry)

        return entries

    def _convert_transaction(
        self, txn: dict[str, Any], filepath: str
    ) -> data.Transaction | None:
        """Convert a single transaction to a Beancount entry.

        Args:
            txn: Transaction data from JSON
            filepath: Path to the source file (for metadata)

        Returns:
            A Beancount Transaction directive or None if conversion fails
        """
        try:
            # Parse dates
            posting_date = self._parse_date(txn["postingDate"])
            txn_date = txn.get("txnDate", "")

            # Build metadata
            meta = data.new_metadata(filepath, 0)
            if txn.get("cardNo"):
                meta["cardNo"] = txn["cardNo"]
            if txn_date:
                meta["tnxDate"] = self._format_date(txn_date)
            if txn.get("txnLoc"):
                meta["tnxLoc"] = txn["txnLoc"]

            # Get description
            description = txn.get("description", "").strip()

            # Get amounts
            ntd_amount = Decimal(txn["ntdAmount"])
            is_foreign = txn.get("isForeignTxn", False)
            foreign_amount = txn.get("amount", "0")
            foreign_currency = txn.get("amtCy", "").strip()

            # Determine accounts based on configuration
            if self.config:
                credit_card_account, expense_account, payment_asset_account = (
                    self.config.get_accounts_for_transaction(txn)
                )
                # Apply CLI overrides if they were explicitly provided
                if self._explicit_credit_card:
                    credit_card_account = self._explicit_credit_card
                if self._explicit_expense:
                    expense_account = self._explicit_expense
                if self._explicit_payment_asset:
                    payment_asset_account = self._explicit_payment_asset
            else:
                credit_card_account = self.credit_card_account
                expense_account = self.expense_account
                payment_asset_account = self.payment_asset_account

            # Create postings based on transaction type
            postings = []

            # Foreign currency transaction (check this first, regardless of sign)
            if is_foreign and foreign_currency and foreign_amount:
                foreign_amt = Decimal(foreign_amount)
                # Calculate per-unit price (total TWD / foreign currency units)
                # This is equivalent to Beancount's @@ to @ conversion
                per_unit_price = ntd_amount / foreign_amt
                postings.append(
                    data.Posting(
                        account=expense_account,
                        units=Amount(foreign_amt, foreign_currency),
                        cost=None,
                        price=Amount(per_unit_price, "TWD"),  # Per-unit price in TWD
                        flag=None,
                        meta=None,
                    )
                )
                postings.append(
                    data.Posting(
                        account=credit_card_account,
                        units=None,  # Balancing posting
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
            # Payment transaction (negative amount, non-foreign)
            elif ntd_amount < 0:
                postings.append(
                    data.Posting(
                        account=credit_card_account,
                        units=Amount(ntd_amount, "TWD"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
                postings.append(
                    data.Posting(
                        account=payment_asset_account,
                        units=None,  # Balancing posting
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
            # Regular TWD transaction
            else:
                postings.append(
                    data.Posting(
                        account=expense_account,
                        units=Amount(ntd_amount, "TWD"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
                postings.append(
                    data.Posting(
                        account=credit_card_account,
                        units=None,  # Balancing posting
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )

            # Create transaction
            return data.Transaction(
                meta=meta,
                date=posting_date,
                flag="*",
                payee=None,
                narration=description,
                tags=set(),
                links=set(),
                postings=postings,
            )

        except (KeyError, ValueError) as e:
            # Log error but don't stop processing other transactions
            print(f"Warning: Failed to convert transaction: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime.date:
        """Parse date from HSBC format (YYYY/MM/DD).

        Args:
            date_str: Date string in format YYYY/MM/DD

        Returns:
            A date object
        """
        return datetime.strptime(date_str, "%Y/%m/%d").date()

    def _format_date(self, date_str: str) -> str:
        """Format date to YYYY-MM-DD format.

        Args:
            date_str: Date string in format YYYY/MM/DD

        Returns:
            Date string in format YYYY-MM-DD
        """
        date_obj = self._parse_date(date_str)
        return date_obj.strftime("%Y-%m-%d")
