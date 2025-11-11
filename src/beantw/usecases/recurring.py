"""Use case for adding recurring transactions to Beancount files."""

from datetime import date
from pathlib import Path
from typing import Protocol

from beancount.core import data

from beantw.config import RecurringTransaction


# Use case defines its own protocols - services implement these
# This follows Clean Architecture: dependencies point FROM services TO use case


class RecurringCalculatorProtocol(Protocol):
    """Protocol for calculating recurring transaction dates.

    Services implementing this protocol handle the business logic of
    determining when a recurring transaction should occur.
    """

    def calculate_next_occurrence(
        self, recurring_txn: RecurringTransaction, current_date: date
    ) -> date | None:
        """Calculate the next occurrence date for a recurring transaction.

        Args:
            recurring_txn: Recurring transaction definition
            current_date: Current date

        Returns:
            Next occurrence date if applicable, None otherwise
        """
        ...


class BookPathResolverProtocol(Protocol):
    """Protocol for resolving book file paths.

    Services implementing this protocol handle the logic of converting
    template strings into concrete file paths.
    """

    def resolve_path(
        self, template: str, transaction_date: date, base_dir: Path
    ) -> Path:
        """Resolve a book template path to an actual file path.

        Args:
            template: Template path with variables like {{year}}, {{month}}
            transaction_date: Date for the transaction
            base_dir: Base directory for resolving relative paths

        Returns:
            Resolved absolute path
        """
        ...


class TransactionBuilderProtocol(Protocol):
    """Protocol for building Beancount transactions.

    Services implementing this protocol handle the creation of
    Beancount transaction objects from recurring transaction definitions.
    """

    def build_transaction(
        self, recurring_txn: RecurringTransaction, transaction_date: date
    ) -> data.Transaction:
        """Build a Beancount transaction from a recurring transaction definition.

        Args:
            recurring_txn: Recurring transaction definition
            transaction_date: Date for the transaction

        Returns:
            Beancount transaction
        """
        ...


class BeancountRepositoryProtocol(Protocol):
    """Protocol for Beancount file repository operations.

    Services implementing this protocol handle persistence of
    transactions to Beancount files.
    """

    def add_transaction_if_not_exists(
        self, filepath: Path, transaction: data.Transaction
    ) -> bool:
        """Add a transaction to a file if it doesn't already exist.

        Args:
            filepath: Path to the Beancount file
            transaction: Transaction to add

        Returns:
            True if transaction was added, False if it already existed
        """
        ...


class RecurringTransactionUseCase:
    """Use case for adding recurring transactions to Beancount files.

    This use case orchestrates the services needed to process recurring
    transactions, following Clean Architecture principles where the use case
    coordinates domain services rather than implementing business logic directly.
    """

    def __init__(
        self,
        recurring_transactions: list[RecurringTransaction],
        base_dir: str,
        current_date: date,
        calculator: RecurringCalculatorProtocol,
        path_resolver: BookPathResolverProtocol,
        transaction_builder: TransactionBuilderProtocol,
        repository: BeancountRepositoryProtocol,
    ):
        """Initialize the use case with required services.

        All dependencies must be injected by the caller (composition root).
        The use case does not create its own dependencies.

        Args:
            recurring_transactions: List of recurring transaction definitions
            base_dir: Base directory for resolving relative paths
            current_date: Current date for determining occurrences
            calculator: Service for calculating next occurrences
            path_resolver: Service for resolving template paths
            transaction_builder: Service for building transactions
            repository: Repository for managing Beancount files
        """
        self.recurring_transactions = recurring_transactions
        self.base_dir = Path(base_dir)
        self.current_date = current_date
        self.calculator = calculator
        self.path_resolver = path_resolver
        self.transaction_builder = transaction_builder
        self.repository = repository

    def execute(self) -> None:
        """Execute the recurring transaction processing.

        For each recurring transaction, this use case:
        1. Calculates when the next occurrence should be
        2. Resolves where the transaction should be saved
        3. Builds the transaction
        4. Adds it to the file if it doesn't already exist
        """
        for recurring_txn in self.recurring_transactions:
            self._process_recurring_transaction(recurring_txn)

    def _process_recurring_transaction(
        self, recurring_txn: RecurringTransaction
    ) -> None:
        """Process a single recurring transaction.

        Args:
            recurring_txn: The recurring transaction to process
        """
        # Calculate when this transaction should occur
        next_occurrence = self.calculator.calculate_next_occurrence(
            recurring_txn, self.current_date
        )

        # Skip if we haven't reached the next occurrence yet
        if next_occurrence is None or self.current_date < next_occurrence:
            return

        # Resolve where to save the transaction
        book_path = self.path_resolver.resolve_path(
            recurring_txn.book, next_occurrence, self.base_dir
        )

        # Build the transaction
        transaction = self.transaction_builder.build_transaction(
            recurring_txn, next_occurrence
        )

        # Add to file if it doesn't exist
        self.repository.add_transaction_if_not_exists(book_path, transaction)
