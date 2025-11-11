"""Service for calculating recurring transaction occurrences."""

from datetime import date, timedelta
from typing import Protocol

from dateutil.relativedelta import relativedelta

from beantw.config import RecurringFrequency, RecurringTransaction


class RecurringCalculatorProtocol(Protocol):
    """Protocol for calculating recurring transaction dates."""

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


class RecurringCalculator:
    """Service for calculating when recurring transactions should occur.

    This service encapsulates the business logic for determining the next
    occurrence date of a recurring transaction based on its frequency.
    """

    def calculate_next_occurrence(
        self, recurring_txn: RecurringTransaction, current_date: date
    ) -> date | None:
        """Calculate the next occurrence date for a recurring transaction.

        This method calculates which occurrence period the current date falls into,
        and returns the date for that occurrence. Returns None if we haven't reached
        the start date yet.

        Args:
            recurring_txn: Recurring transaction definition
            current_date: Current date

        Returns:
            Next occurrence date if we're past the start date, None otherwise

        Raises:
            ValueError: If frequency is not supported
        """
        start = recurring_txn.start_date

        # If we haven't reached the start date yet
        if current_date < start:
            return None

        frequency = recurring_txn.frequency

        # Calculate which occurrence period we're in
        if frequency == RecurringFrequency.DAILY:
            days_since_start = (current_date - start).days
            return start + timedelta(days=days_since_start)

        elif frequency == RecurringFrequency.WEEKLY:
            weeks_since_start = (current_date - start).days // 7
            return start + timedelta(weeks=weeks_since_start)

        elif frequency == RecurringFrequency.MONTHLY:
            months_since_start = (
                (current_date.year - start.year) * 12 + current_date.month - start.month
            )
            return start + relativedelta(months=months_since_start)

        elif frequency == RecurringFrequency.YEARLY:
            years_since_start = current_date.year - start.year
            return start + relativedelta(years=years_since_start)

        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
