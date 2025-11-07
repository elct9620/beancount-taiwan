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
        source_account: str | None = None,
        target_account: str | None = None,
        config: HSBCCreditCardConfig | None = None,
    ):
        """Initialize the HSBC credit card importer.

        Args:
            source_account: The credit card liability account (overrides config)
            target_account: The default expense account (overrides config)
            config: Optional configuration object for category matching
        """
        self.config = config
        self._explicit_target = target_account  # Track if target was explicitly set

        if config:
            self.source_account = source_account or config.source_account
            self.target_account = target_account or config.target_account
        else:
            self.source_account = (
                source_account or "Liabilities:CreditCard:HSBC:Travelers"
            )
            self.target_account = target_account or "Expenses:Others"

    def account(self, filepath: str) -> str:
        """Return the primary account for this importer.

        Args:
            filepath: Path to the file being imported

        Returns:
            The credit card account name
        """
        return self.source_account

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

            # Determine the other account using category matching
            # If target was explicitly set via CLI, use it; otherwise use config matching
            if self._explicit_target:
                other_account = self.target_account
            elif self.config:
                other_account = self.config.get_account_for_transaction(txn)
            else:
                other_account = self.target_account

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
                        account=other_account,
                        units=Amount(foreign_amt, foreign_currency),
                        cost=None,
                        price=Amount(per_unit_price, "TWD"),  # Per-unit price in TWD
                        flag=None,
                        meta=None,
                    )
                )
                postings.append(
                    data.Posting(
                        account=self.source_account,
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
                        account=other_account,
                        units=Amount(
                            ntd_amount, "TWD"
                        ),  # Negative amount - money leaves account
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
                postings.append(
                    data.Posting(
                        account=self.source_account,
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
                        account=other_account,
                        units=Amount(ntd_amount, "TWD"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                )
                postings.append(
                    data.Posting(
                        account=self.source_account,
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
