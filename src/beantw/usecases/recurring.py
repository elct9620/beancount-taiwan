"""Use case for adding recurring transactions to Beancount files."""

from datetime import date
from pathlib import Path

from beantw.config import RecurringTransaction
from beantw.services.beancount_file_service import (
    BeancountRepository,
    BeancountRepositoryProtocol,
)
from beantw.services.book_path_resolver import (
    BookPathResolver,
    BookPathResolverProtocol,
)
from beantw.services.recurring_calculator import (
    RecurringCalculator,
    RecurringCalculatorProtocol,
)
from beantw.services.transaction_builder import (
    TransactionBuilder,
    TransactionBuilderProtocol,
)


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
        current_date: date | None = None,
        calculator: RecurringCalculatorProtocol | None = None,
        path_resolver: BookPathResolverProtocol | None = None,
        transaction_builder: TransactionBuilderProtocol | None = None,
        repository: BeancountRepositoryProtocol | None = None,
    ):
        """Initialize the use case with required services.

        Args:
            recurring_transactions: List of recurring transaction definitions
            base_dir: Base directory for resolving relative paths
            current_date: Current date (defaults to today, provided for testing)
            calculator: Service for calculating next occurrences
            path_resolver: Service for resolving template paths
            transaction_builder: Service for building transactions
            repository: Repository for managing Beancount files
        """
        self.recurring_transactions = recurring_transactions
        self.base_dir = Path(base_dir)
        self.current_date = current_date or date.today()

        # Initialize services with defaults if not provided
        self.calculator = calculator or RecurringCalculator()
        self.path_resolver = path_resolver or BookPathResolver()
        self.transaction_builder = transaction_builder or TransactionBuilder()
        self.repository = repository or BeancountRepository()

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
