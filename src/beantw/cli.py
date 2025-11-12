"""CLI for beancount-taiwan."""

from pathlib import Path

import typer

from beantw.config import HSBCCreditCardConfig, RecurringTransactionConfig
from beantw.importers.hsbc_credit_card import HSBCCreditCardImporter
from beantw.usecases.convert import ConvertUseCase
from beantw.usecases.recurring import RecurringTransactionUseCase
from beantw.usecases.refresh import RefreshUseCase

app = typer.Typer(help="Beancount data importer for Taiwanese banks and credit cards")


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
    config_file: Path | None = typer.Option(
        None,
        "--config",
        "-f",
        help="Path to YAML configuration file with account mappings and category rules (default: config/hsbc_credit_card_importer.yaml if exists)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    source_account: str | None = typer.Option(
        None,
        "--source-account",
        "-s",
        help="Credit card liability account (overrides config file)",
    ),
    target_account: str | None = typer.Option(
        None,
        "--target-account",
        "-t",
        help="Default expense account for transactions (overrides config file)",
    ),
):
    """Convert HSBC credit card statement JSON to Beancount format.

    Reads an HSBC credit card statement JSON file (manually copied from HSBC API)
    and converts it to Beancount entries, outputting them to standard output.

    You can use a YAML configuration file to specify account mappings and category rules
    for automatically categorizing transactions based on description patterns.
    If no config file is specified, the tool will automatically look for
    config/hsbc_credit_card_importer.yaml in the current directory.
    Command-line options override config file settings.
    """
    try:
        # Determine which config file to use
        config_path = config_file
        if config_path is None:
            # Check for default config file location
            default_config = Path("config/hsbc_credit_card_importer.yaml")
            if default_config.exists():
                config_path = default_config

        # Load configuration if available
        config = HSBCCreditCardConfig(config_path) if config_path else None

        # Create importer with configuration
        importer = HSBCCreditCardImporter(
            source_account=source_account,
            target_account=target_account,
            config=config,
        )

        # Create and execute use case
        use_case = ConvertUseCase(importer)
        result = use_case.execute(str(filepath))

        # Output result
        typer.echo(result)

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def refresh(
    directory: Path = typer.Argument(
        "books",
        help="Directory to scan for Beancount files (default: books/)",
        file_okay=False,
        dir_okay=True,
    ),
):
    """Recursively refresh Beancount index files in a directory.

    Scans the specified directory (default: books/) for Beancount files and
    automatically creates or updates index files (index.bean, books.bean, etc.)
    in each directory. Index files will contain include statements for all
    Beancount files in the same directory.

    The command processes directories recursively, so nested directory structures
    are fully supported. Existing index files will be updated to include new files
    while preserving any existing include statements.
    """
    try:
        # Create and execute use case
        use_case = RefreshUseCase()
        use_case.execute(str(directory))

        typer.echo(f"Successfully refreshed index files in {directory}")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def recurring(
    config_file: Path | None = typer.Option(
        None,
        "--config",
        "-f",
        help="Path to YAML configuration file with recurring transaction definitions (default: config/recurring.yaml if exists)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    base_dir: Path = typer.Option(
        Path.cwd(),
        "--base-dir",
        "-d",
        help="Base directory for resolving relative paths (default: current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
):
    """Add recurring transactions to Beancount files.

    Processes recurring transaction definitions from a configuration file and
    adds the next occurrence of each transaction to the appropriate Beancount file
    if it doesn't already exist.

    The configuration file defines recurring transactions with their frequency,
    amount, accounts, and target Beancount file path (supporting template variables).

    By default, looks for config/recurring.yaml in the current directory.
    """
    try:
        # Determine which config file to use
        config_path = config_file
        if config_path is None:
            # Check for default config file locations
            for default_name in ["config/recurring.yaml", "config/recurring.yml"]:
                default_config = Path(default_name)
                if default_config.exists():
                    config_path = default_config
                    break

        if config_path is None:
            typer.echo(
                "Error: No configuration file found. Please create config/recurring.yaml or specify --config",
                err=True,
            )
            raise typer.Exit(code=1)

        # Load configuration
        config = RecurringTransactionConfig(config_path)

        if not config.recurring_transactions:
            typer.echo("No recurring transactions defined in configuration file.")
            return

        # Composition Root: Instantiate all services here
        # This is the ONLY place where concrete implementations are created
        from datetime import date

        from beantw.services.beancount_file_service import BeancountRepository
        from beantw.services.book_path_resolver import BookPathResolver
        from beantw.services.recurring_calculator import RecurringCalculator
        from beantw.services.transaction_builder import TransactionBuilder

        calculator = RecurringCalculator()
        path_resolver = BookPathResolver()
        transaction_builder = TransactionBuilder()
        repository = BeancountRepository()
        current_date = date.today()

        # Create and execute use case with all dependencies injected
        use_case = RecurringTransactionUseCase(
            recurring_transactions=config.recurring_transactions,
            base_dir=str(base_dir),
            current_date=current_date,
            calculator=calculator,
            path_resolver=path_resolver,
            transaction_builder=transaction_builder,
            repository=repository,
        )
        use_case.execute()

        typer.echo(
            f"Successfully processed {len(config.recurring_transactions)} recurring transaction(s)"
        )

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
