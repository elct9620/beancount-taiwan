"""Service for reading and writing Beancount files.

This module provides file system operations for reading and writing
Beancount transaction files.
"""

from datetime import date
from pathlib import Path

from beancount.core import data
from beancount.parser import parser, printer


class DefaultBeancountFileService:
    """Service for managing Beancount transaction files.

    This service handles reading, parsing, and writing Beancount files,
    as well as checking for transaction existence.
    """

    def read_file(self, filepath: Path) -> list[data.Directive]:
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

    def write_transaction(self, filepath: Path, transaction: data.Transaction) -> None:
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

    def transaction_exists(
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

        entries = self.read_file(filepath)

        # Check for matching transaction
        for entry in entries:
            if isinstance(entry, data.Transaction):
                if entry.date == transaction_date and entry.narration == description:
                    return True

        return False
