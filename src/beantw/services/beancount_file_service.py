"""Repository for managing Beancount transaction files.

This module provides higher-level operations for working with Beancount files,
following the repository pattern to abstract file system operations.
"""

from datetime import date
from pathlib import Path
from typing import Protocol

from beancount.core import data
from beancount.parser import parser, printer


class BeancountRepositoryProtocol(Protocol):
    """Protocol for Beancount file repository operations."""

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


class BeancountRepository:
    """Repository for managing Beancount transaction files.

    This repository provides semantic, high-level operations for managing
    transactions in Beancount files, abstracting away low-level file operations.
    """

    def add_transaction_if_not_exists(
        self, filepath: Path, transaction: data.Transaction
    ) -> bool:
        """Add a transaction to a file if it doesn't already exist.

        This operation encapsulates the complete business logic of:
        1. Checking if the transaction already exists
        2. If not, appending it to the file (creating file/directories if needed)

        Args:
            filepath: Path to the Beancount file
            transaction: Transaction to add

        Returns:
            True if transaction was added, False if it already existed
        """
        # Check if transaction already exists
        if self._transaction_exists(filepath, transaction.date, transaction.narration):
            return False

        # Add the transaction
        self._append_transaction(filepath, transaction)
        return True

    def _transaction_exists(
        self, filepath: Path, transaction_date: date, description: str
    ) -> bool:
        """Check if a transaction with given date and description exists.

        Args:
            filepath: Path to the Beancount file
            transaction_date: Date of the transaction
            description: Description (narration) of the transaction

        Returns:
            True if transaction exists, False otherwise
        """
        if not filepath.exists():
            return False

        entries = self._read_file(filepath)

        # Check for matching transaction
        for entry in entries:
            if isinstance(entry, data.Transaction):
                if entry.date == transaction_date and entry.narration == description:
                    return True

        return False

    def _read_file(self, filepath: Path) -> list[data.Directive]:
        """Read and parse a Beancount file.

        Args:
            filepath: Path to the Beancount file

        Returns:
            List of Beancount directives, or empty list if file doesn't exist
        """
        if not filepath.exists():
            return []

        try:
            entries, errors, _ = parser.parse_file(str(filepath))
            if errors:
                # Log errors but don't fail - just return what we could parse
                pass
            return entries
        except Exception:
            # If we can't parse the file, return empty list
            return []

    def _append_transaction(
        self, filepath: Path, transaction: data.Transaction
    ) -> None:
        """Append a transaction to a Beancount file.

        Creates the file and parent directories if they don't exist.

        Args:
            filepath: Path to the Beancount file
            transaction: Transaction to append
        """
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Format the transaction
        txn_str = printer.format_entry(transaction)

        # Append to file (create if doesn't exist)
        if filepath.exists():
            # Read existing content
            content = filepath.read_text(encoding="utf-8")
            # Append transaction with newline
            if content and not content.endswith("\n"):
                content += "\n"
            content += txn_str + "\n"
            filepath.write_text(content, encoding="utf-8")
        else:
            # Create new file with transaction
            filepath.write_text(txn_str + "\n", encoding="utf-8")


# Alias for backwards compatibility
DefaultBeancountFileService = BeancountRepository
