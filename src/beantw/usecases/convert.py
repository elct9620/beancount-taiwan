"""Use case for converting financial data to Beancount format."""

from typing import Protocol

from beancount.core import data
from beancount.parser import printer


class ImporterProtocol(Protocol):
    """Protocol defining the interface for importers.

    This follows Clean Architecture's dependency inversion principle,
    allowing the use case to depend on an abstraction rather than concrete implementations.
    """

    def identify(self, filepath: str) -> bool:
        """Identify if the file can be handled by this importer.

        Args:
            filepath: Path to the file to identify

        Returns:
            True if the file can be handled, False otherwise
        """
        ...

    def extract(self, filepath: str, existing_entries=None) -> list[data.Directive]:
        """Extract transactions from the file.

        Args:
            filepath: Path to the file
            existing_entries: Existing entries (optional)

        Returns:
            List of Beancount directives
        """
        ...


class ConvertUseCase:
    """Use case for converting financial data to Beancount entries.

    This use case encapsulates the business logic for converting financial data
    without depending on specific framework implementations.
    """

    def __init__(self, importer: ImporterProtocol):
        """Initialize the use case with an importer.

        Args:
            importer: An importer that implements ImporterProtocol
        """
        self.importer = importer

    def execute(self, filepath: str) -> str:
        """Execute the conversion of financial data to Beancount format.

        Args:
            filepath: Path to the financial data file

        Returns:
            A string containing Beancount entries in text format

        Raises:
            ValueError: If the file is not valid for the importer
        """
        # Validate that the file can be handled by this importer
        if not self.importer.identify(filepath):
            raise ValueError(
                f"File {filepath} is not recognized as a valid file for this importer"
            )

        # Extract entries from the file
        entries = self.importer.extract(filepath)

        # Convert entries to Beancount text format
        output_lines = []
        for entry in entries:
            entry_str = printer.format_entry(entry)
            output_lines.append(entry_str)

        return "\n".join(output_lines)
