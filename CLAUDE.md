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
- **Entry Point**: `src/beantw/cli.py` contains the typer-based CLI
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

## Architecture

The project follows **Clean Architecture** principles (see docs/ARCHITECTURE.md for full details):

### Layers
- **CLI (Adapters)**: `cli.py` handles command-line arguments and invokes use cases
- **Use Cases**: Core business logic in `usecases/` (e.g., `convert_hsbc_credit_card.py`, `convert_esunsec.py`)
  - Should NOT depend on external libraries/frameworks
  - Use dependency inversion - depend on abstractions, not implementations
- **Importers (Frameworks & Drivers)**: Low-level modules in `importers/` that interact with Beancount and parse specific formats
  - Implement interfaces defined by use cases

### Adding New Importers

Follow BDD + TDD workflow when adding support for a new data format:

1. **Read feature documentation** in `docs/features/import_[format_identifier].md` (must exist before implementation)
2. **Write tests** in `tests/test_importers/test_[format_identifier].py` based on feature requirements
3. **Implement parser** in `src/beantw/importers/[format_identifier].py` (implements interface from use case)
4. **Implement use case** in `src/beantw/usecases/convert_[format_identifier].py` (pure business logic, no framework dependencies)
5. **Add CLI command** in `cli.py` using `@app.command()` that instantiates and invokes the use case

Note: Use descriptive format identifiers that include both institution and data type (e.g., `hsbc_credit_card` for HSBC credit cards, `esunsec` for E.SUN Securities broker data).

### Key Dependencies

- **typer>=0.15.1**: CLI framework with automatic help generation
- **beangulp>=0.2.0**: Importer framework for Beancount
- **beancount>=3.0.0**: Core accounting engine and transaction format

## Testing

- Tests are written using pytest
- Development dependencies include pytest>=8.4.2
- Place tests in a `tests/` directory (to be created) following pytest conventions
