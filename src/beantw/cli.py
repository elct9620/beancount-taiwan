"""CLI for beancount-taiwan."""

from pathlib import Path

import typer

from beantw.importers.hsbc_credit_card import HSBCCreditCardImporter
from beantw.usecases.convert_hsbc_credit_card import ConvertHSBCCreditCardUseCase

app = typer.Typer(help="Beancount data importer for Taiwanese banks and credit cards")


@app.command()
def hello():
    """Test command to verify CLI is working."""
    typer.echo("Hello from beancount-taiwan!")


@app.command()
def convert(
    filepath: Path = typer.Argument(
        ...,
        help="Path to the HSBC credit card statement JSON file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    credit_card_account: str = typer.Option(
        "Liabilities:CreditCard:HSBC:Travelers",
        "--credit-card-account",
        "-c",
        help="Credit card liability account",
    ),
    expense_account: str = typer.Option(
        "Expenses:Life",
        "--expense-account",
        "-e",
        help="Default expense account",
    ),
    payment_asset_account: str = typer.Option(
        "Assets:Bank:Checking",
        "--payment-asset-account",
        "-p",
        help="Asset account for payments",
    ),
):
    """Convert HSBC credit card statement JSON to Beancount format.

    Reads an HSBC credit card statement JSON file (manually copied from HSBC API)
    and converts it to Beancount entries, outputting them to standard output.
    """
    try:
        # Create importer with configuration
        importer = HSBCCreditCardImporter(
            credit_card_account=credit_card_account,
            expense_account=expense_account,
            payment_asset_account=payment_asset_account,
        )

        # Create and execute use case
        use_case = ConvertHSBCCreditCardUseCase(importer)
        result = use_case.execute(str(filepath))

        # Output result
        typer.echo(result)

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(code=1)


def main():
    """Entry point for the bean-tw command."""
    app()


if __name__ == "__main__":
    main()
