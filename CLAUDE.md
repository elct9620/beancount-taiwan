# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Beancount data importer package tailored for Taiwanese banks, credit cards, and local transaction formats. The package provides a CLI tool called `bean-tw` for importing financial data into Beancount format.

## Development Environment

This project uses:
- **Package Manager**: `uv` (Python package manager)
- **Environment Manager**: Devbox with direnv integration (automatically activated when entering the directory)
- **Python Version**: 3.11+ (specified in pyproject.toml)

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

# Example: Convert HSBC credit card statement
bean-tw convert path/to/hsbc_statement.json

# With custom config file
bean-tw convert path/to/hsbc_statement.json --config my_config.yaml

# Override specific accounts via CLI
bean-tw convert path/to/hsbc_statement.json --source-account "Liabilities:CreditCard:HSBC:MyCard" --target-account "Expenses:Shopping"
```

**Current Importers**:
- HSBC Credit Card (`convert` command) - Converts HSBC credit card statement JSON to Beancount format

### Development Tools
```bash
# Run linter (use uv run for consistent environment)
uv run ruff check .

# Run formatter
uv run ruff format .

# Run tests
uv run pytest

# Run specific test
uv run pytest path/to/test_file.py::test_function

# Run specific test class
uv run pytest tests/test_importers/test_hsbc_credit_card.py::TestHSBCCreditCardImporter
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
- **pyyaml>=6.0.0**: YAML configuration file parsing

### Configuration System

The project uses YAML-based configuration files for importers:
- **Location**: `config/[importer_name]_importer.yaml` (e.g., `config/hsbc_credit_card_importer.yaml`)
- **Auto-discovery**: CLI commands automatically look for default config in `config/` directory if no `--config` option provided
- **Structure**: Each importer has its own config class in `src/beantw/config.py`
- **Pattern Matching**: Configs support regex-based category matching for auto-categorizing transactions
- **Config Class**: `HSBCCreditCardConfig` demonstrates the pattern - loads default accounts and category rules
- **CLI Overrides**: Command-line options (`--source-account`, `--target-account`) override config file settings

Example config structure:
```yaml
default:
  source: Liabilities:CreditCard:HSBC:Travelers  # Credit card account
  target: Expenses:Others                         # Default expense account

categories:
  - pattern: "^PAYMENT RECEIVED$"                 # Regex pattern
    account: Assets:Bank:Checking                 # Account for matching transactions
  - pattern: "^國外交易手續費$"
    account: Expenses:BankFees
```

### Protocol-Based Design

Use cases define **Protocol** classes (Python's structural typing) instead of abstract base classes:
- Protocols define the interface importers must implement (e.g., `HSBCCreditCardImporterProtocol`)
- Methods: `identify(filepath: str) -> bool` and `extract(filepath: str) -> list[data.Directive]`
- This follows dependency inversion - use cases depend on abstractions, not concrete implementations

### Importer Implementation Details

#### Transaction Type Handling (HSBC Credit Card Example)

The HSBC importer handles three transaction types with different posting logic:

1. **Foreign Currency Transactions** (`isForeignTxn=true`):
   - Uses per-unit price conversion (not total price `@@`)
   - Calculates: `per_unit_price = ntd_amount / foreign_amount`
   - Creates posting with `Amount(foreign_amt, currency)` and `price=Amount(per_unit_price, "TWD")`
   - Balancing posting on credit card account

2. **Payment Transactions** (negative `ntdAmount`):
   - Negative amounts indicate payments received
   - First posting: target account (e.g., `Assets:Bank:Checking`) with negative TWD amount
   - Balancing posting on credit card account reduces liability

3. **Regular TWD Transactions**:
   - Positive `ntdAmount` for expenses
   - First posting: expense/target account with TWD amount
   - Balancing posting on credit card account

**CLI Override Behavior**: If `--target-account` is explicitly provided via CLI, it overrides config-based category matching for all transactions.

## Testing

- Tests are written using pytest (pytest>=8.4.2)
- Test structure mirrors source structure: `tests/test_importers/` maps to `src/beantw/importers/`
- Feature documentation in `docs/features/` contains BDD scenarios that guide test implementation
