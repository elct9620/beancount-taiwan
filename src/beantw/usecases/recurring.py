"""Use case for adding recurring transactions to Beancount files."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from beancount.core import amount, data
from dateutil.relativedelta import relativedelta

from beantw.config import RecurringTransaction


class DateProvider(Protocol):
    """Protocol for providing the current date (for testing)."""

    def today(self) -> date:
        """Get the current date.

        Returns:
            The current date
        """
        ...


class DefaultDateProvider:
    """Default implementation of DateProvider using system date."""

    def today(self) -> date:
        """Get the current date from system.

        Returns:
            The current date
        """
        return date.today()


class BeancountFileService(Protocol):
    """Protocol for reading and writing Beancount files."""

    def read_file(self, filepath: Path) -> list[data.Directive]:
        """Read and parse a Beancount file.

        Args:
            filepath: Path to the Beancount file

        Returns:
            List of Beancount directives
        """
        ...

    def write_transaction(self, filepath: Path, transaction: data.Transaction) -> None:
        """Append a transaction to a Beancount file.

        Args:
            filepath: Path to the Beancount file
            transaction: Transaction to append
        """
        ...

    def transaction_exists(
        self, filepath: Path, transaction_date: date, description: str
    ) -> bool:
        """Check if a transaction with given date and description exists.

        Args:
            filepath: Path to the Beancount file
            transaction_date: Date of the transaction
            description: Description of the transaction

        Returns:
            True if transaction exists, False otherwise
        """
        ...


class RecurringTransactionUseCase:
    """Use case for adding recurring transactions to Beancount files.

    This use case processes recurring transaction definitions and adds
    the next occurrence to the appropriate Beancount file if it doesn't
    already exist.
    """

    def __init__(
        self,
        recurring_transactions: list[RecurringTransaction],
        base_dir: str,
        date_provider: DateProvider | None = None,
        file_service: BeancountFileService | None = None,
    ):
        """Initialize the use case.

        Args:
            recurring_transactions: List of recurring transaction definitions
            base_dir: Base directory for resolving relative paths
            date_provider: Provider for current date (defaults to system date)
            file_service: Service for file operations (defaults to DefaultBeancountFileService)
        """
        self.recurring_transactions = recurring_transactions
        self.base_dir = Path(base_dir)
        self.date_provider = date_provider or DefaultDateProvider()
        # Import here to avoid circular dependency
        from beantw.services.beancount_file_service import (
            DefaultBeancountFileService,
        )

        self.file_service = file_service or DefaultBeancountFileService()

    def execute(self) -> None:
        """Execute the recurring transaction processing.

        For each recurring transaction:
        1. Calculate the next occurrence date
        2. Check if we're past that date
        3. Resolve the book template path
        4. Check if transaction already exists
        5. If not, add it to the file
        """
        current_date = self.date_provider.today()

        for recurring_txn in self.recurring_transactions:
            # Calculate next occurrence
            next_occurrence = self._calculate_next_occurrence(
                recurring_txn, current_date
            )

            # Skip if we haven't reached the next occurrence yet
            if next_occurrence is None or current_date < next_occurrence:
                continue

            # Resolve the book template to actual file path
            book_path = self._resolve_book_path(recurring_txn.book, next_occurrence)

            # Check if transaction already exists
            if self.file_service.transaction_exists(
                book_path, next_occurrence, recurring_txn.description
            ):
                continue

            # Create and add the transaction
            transaction = self._create_transaction(recurring_txn, next_occurrence)
            self.file_service.write_transaction(book_path, transaction)

    def _calculate_next_occurrence(
        self, recurring_txn: RecurringTransaction, current_date: date
    ) -> date | None:
        """Calculate the next occurrence date for a recurring transaction.

        Args:
            recurring_txn: Recurring transaction definition
            current_date: Current date

        Returns:
            Next occurrence date, or None if not applicable
        """
        start = recurring_txn.start_date
        frequency = recurring_txn.frequency.lower()

        # If we haven't reached the start date yet
        if current_date < start:
            return None

        # Calculate how many periods have passed since start
        if frequency == "daily":
            delta = (current_date - start).days
            next_occurrence = start + timedelta(days=delta)
        elif frequency == "weekly":
            delta = (current_date - start).days // 7
            next_occurrence = start + timedelta(weeks=delta)
        elif frequency == "monthly":
            # Calculate months difference
            months_diff = (
                (current_date.year - start.year) * 12 + current_date.month - start.month
            )
            next_occurrence = start + relativedelta(months=months_diff)
        elif frequency == "yearly":
            years_diff = current_date.year - start.year
            next_occurrence = start + relativedelta(years=years_diff)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")

        # If we've calculated a date in the past (before current_date),
        # and it matches current month/period, use it
        # This handles the case where we run the command mid-month
        if next_occurrence <= current_date:
            return next_occurrence

        return None

    def _resolve_book_path(self, book_template: str, txn_date: date) -> Path:
        """Resolve book template path with date variables.

        Args:
            book_template: Template path with variables like {{year}}, {{month}}
            txn_date: Date for the transaction

        Returns:
            Resolved path
        """
        # Create template variables
        template_vars = {
            "year": str(txn_date.year),
            "month": f"{txn_date.month:02d}",
            "day": f"{txn_date.day:02d}",
            "month_name": txn_date.strftime("%B"),
            "month_abbr": txn_date.strftime("%b"),
            "weekday": txn_date.strftime("%A"),
            "weekday_abbr": txn_date.strftime("%a"),
        }

        # Replace template variables
        resolved = book_template
        for var, value in template_vars.items():
            resolved = resolved.replace(f"{{{{{var}}}}}", value)

        # Resolve relative to base directory
        return self.base_dir / resolved

    def _create_transaction(
        self, recurring_txn: RecurringTransaction, txn_date: date
    ) -> data.Transaction:
        """Create a Beancount transaction from recurring transaction definition.

        Args:
            recurring_txn: Recurring transaction definition
            txn_date: Date for the transaction

        Returns:
            Beancount transaction
        """
        # Convert float amount to Decimal with 2 decimal places
        amount_decimal = Decimal(str(recurring_txn.amount)).quantize(Decimal("0.01"))

        # Create postings
        postings = [
            data.Posting(
                account=recurring_txn.target_account,
                units=amount.Amount(amount_decimal, recurring_txn.currency),
                cost=None,
                price=None,
                flag=None,
                meta={},
            ),
            data.Posting(
                account=recurring_txn.source_account,
                units=amount.Amount(-amount_decimal, recurring_txn.currency),
                cost=None,
                price=None,
                flag=None,
                meta={},
            ),
        ]

        # Create transaction
        transaction = data.Transaction(
            meta={},
            date=txn_date,
            flag="*",
            payee=None,
            narration=recurring_txn.description,
            tags=set(),
            links=set(),
            postings=postings,
        )

        return transaction
