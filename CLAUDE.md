# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Beancount data importer package tailored for Taiwanese banks, credit cards, and local transaction formats. The package provides a CLI tool called `bean-tw` for importing financial data into Beancount format.

## Development Environment

This project uses:
- **Package Manager**: `uv` (Python package manager)
- **Environment Manager**: Devbox with direnv integration (automatically activated when entering the directory)
- **Python Version**: 3.13+

## Package Structure

- **src-layout**: The project uses standard Python src-layout
- **Entry Point**: `src/beancount_taiwan/cli.py` contains the typer-based CLI
- **Command**: The `bean-tw` command is configured in `pyproject.toml` under `[project.scripts]`

## Common Commands

### Environment Setup
```bash
# Install dependencies
uv sync
```

### Running the CLI
```bash
# Run via uv (recommended, always uses project's environment)
uv run bean-tw [command]

# Run directly (environment is auto-activated by direnv)
bean-tw [command]
```

### Development Tools
```bash
# Run linter
ruff check .

# Run formatter
ruff format .

# Run tests
pytest

# Run specific test
pytest path/to/test_file.py::test_function
```

## Adding New Importers

When adding support for a new bank or credit card:
1. Create a new module in `src/beancount_taiwan/` for the importer
2. Add a new command in `cli.py` using `@app.command()` decorator
3. Follow typer conventions for CLI interface design
4. Importers should output valid Beancount format

## Architecture Notes

- **CLI Framework**: Uses typer for command-line interface with automatic help generation
- **Beancount Integration**: Depends on beancount>=3.0.0 for transaction format compatibility
- **Modular Design**: Each bank/card importer should be a separate module
- The `cli.py` serves as the command router, individual importers handle parsing logic

## Testing

- Tests are written using pytest
- Development dependencies include pytest>=8.4.2
- Place tests in a `tests/` directory (to be created) following pytest conventions
