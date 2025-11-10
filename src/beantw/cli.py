"""CLI for beancount-taiwan."""

from pathlib import Path

import typer

from beantw.config import HSBCCreditCardConfig
from beantw.importers.hsbc_credit_card import HSBCCreditCardImporter
from beantw.usecases.convert import ConvertUseCase
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


def main():
    """Entry point for the bean-tw command."""
    app()


if __name__ == "__main__":
    main()
