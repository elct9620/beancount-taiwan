"""Service for resolving Beancount book file paths from templates."""

from datetime import date
from pathlib import Path
from typing import Protocol


class BookPathResolverProtocol(Protocol):
    """Protocol for resolving book file paths."""

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


class BookPathResolver:
    """Service for resolving template paths to actual file paths.

    This service handles the business logic of converting template strings
    with date variables into concrete file paths for Beancount files.
    """

    def resolve_path(
        self, template: str, transaction_date: date, base_dir: Path
    ) -> Path:
        """Resolve a book template path to an actual file path.

        Supports the following template variables:
        - {{year}}: Four-digit year (e.g., "2023")
        - {{month}}: Zero-padded month (e.g., "01", "12")
        - {{day}}: Zero-padded day (e.g., "01", "31")
        - {{month_name}}: Full month name (e.g., "January")
        - {{month_abbr}}: Abbreviated month name (e.g., "Jan")
        - {{weekday}}: Full weekday name (e.g., "Monday")
        - {{weekday_abbr}}: Abbreviated weekday name (e.g., "Mon")

        Args:
            template: Template path with variables
            transaction_date: Date for the transaction
            base_dir: Base directory for resolving relative paths

        Returns:
            Resolved absolute path
        """
        # Create template variable mappings
        template_vars = {
            "year": str(transaction_date.year),
            "month": f"{transaction_date.month:02d}",
            "day": f"{transaction_date.day:02d}",
            "month_name": transaction_date.strftime("%B"),
            "month_abbr": transaction_date.strftime("%b"),
            "weekday": transaction_date.strftime("%A"),
            "weekday_abbr": transaction_date.strftime("%a"),
        }

        # Replace all template variables
        resolved = template
        for var, value in template_vars.items():
            resolved = resolved.replace(f"{{{{{var}}}}}", value)

        # Resolve relative to base directory
        return base_dir / resolved
