"""Service for building Beancount transactions."""

from datetime import date
from decimal import Decimal
from typing import Protocol

from beancount.core import amount, data

from beantw.config import RecurringTransaction


class TransactionBuilderProtocol(Protocol):
    """Protocol for building Beancount transactions."""

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


class TransactionBuilder:
    """Service for creating Beancount transactions.

    This service encapsulates the business logic of converting recurring
    transaction definitions into proper Beancount transaction objects.
    """

    def build_transaction(
        self, recurring_txn: RecurringTransaction, transaction_date: date
    ) -> data.Transaction:
        """Build a Beancount transaction from a recurring transaction definition.

        Creates a balanced transaction with:
        - Target account receiving the amount (positive)
        - Source account providing the amount (negative)

        Args:
            recurring_txn: Recurring transaction definition
            transaction_date: Date for the transaction

        Returns:
            Beancount transaction with balanced postings
        """
        # Convert float amount to Decimal with 2 decimal places for proper formatting
        amount_decimal = Decimal(str(recurring_txn.amount)).quantize(Decimal("0.01"))

        # Create balanced postings
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
        return data.Transaction(
            meta={},
            date=transaction_date,
            flag="*",
            payee=None,
            narration=recurring_txn.description,
            tags=set(),
            links=set(),
            postings=postings,
        )
