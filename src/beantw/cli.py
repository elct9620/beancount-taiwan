"""CLI for beancount-taiwan."""

import typer

app = typer.Typer(help="Beancount data importer for Taiwanese banks and credit cards")


@app.command()
def hello():
    """Test command to verify CLI is working."""
    typer.echo("Hello from beancount-taiwan!")


def main():
    """Entry point for the bean-tw command."""
    app()


if __name__ == "__main__":
    main()
