"""Use case for converting HSBC credit card statements to Beancount format."""

from typing import Protocol

from beancount.core import data
from beancount.parser import printer


class HSBCCreditCardImporterProtocol(Protocol):
    """Protocol defining the interface for HSBC credit card importers.

    This follows Clean Architecture's dependency inversion principle,
    allowing the use case to depend on an abstraction rather than a concrete implementation.
    """

    def identify(self, filepath: str) -> bool:
        """Identify if the file is an HSBC credit card statement.

        Args:
            filepath: Path to the file to identify

        Returns:
            True if the file is a valid HSBC credit card statement, False otherwise
        """
        ...

    def extract(self, filepath: str, existing_entries=None) -> list[data.Directive]:
        """Extract transactions from HSBC credit card statement.

        Args:
            filepath: Path to the file
            existing_entries: Existing entries (optional)

        Returns:
            List of Beancount directives
        """
        ...


class ConvertHSBCCreditCardUseCase:
    """Use case for converting HSBC credit card statements to Beancount entries.

    This use case encapsulates the business logic for converting HSBC credit card
    statements without depending on specific framework implementations.
    """

    def __init__(self, importer: HSBCCreditCardImporterProtocol):
        """Initialize the use case with an importer.

        Args:
            importer: An importer that implements HSBCCreditCardImporterProtocol
        """
        self.importer = importer

    def execute(self, filepath: str) -> str:
        """Execute the conversion of HSBC credit card statement to Beancount format.

        Args:
            filepath: Path to the HSBC credit card statement JSON file

        Returns:
            A string containing Beancount entries in text format

        Raises:
            ValueError: If the file is not a valid HSBC credit card statement
        """
        # Validate that the file is an HSBC credit card statement
        if not self.importer.identify(filepath):
            raise ValueError(
                f"File {filepath} is not recognized as a valid HSBC credit card statement"
            )

        # Extract entries from the statement
        entries = self.importer.extract(filepath)

        # Convert entries to Beancount text format
        output_lines = []
        for entry in entries:
            entry_str = printer.format_entry(entry)
            output_lines.append(entry_str)

        return "\n".join(output_lines)
