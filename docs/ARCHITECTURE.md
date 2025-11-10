# Architecture Overview

This document provides an overview of the architecture of the Beancount Taiwan project to guide how to develop, maintain, and extend the system effectively.

## Stack

- Python 3.13
- Typer - Library for building command-line interfaces
- Beangulp - Importer framework for Beancount
- Pytest - Testing framework

## Structure

The Beancount Taiwan is a Python-based command-line application that processes financial data using the Beancount.

```
|- src/
    |- beantw/
        |- __init__.py
        |- services/
            |- __init__.py
            |- index_service.py # Service for managing the index.bean file
        |- importers/
            |- __init__.py
            |- hsbc_credit_card.py # Module for importing HSBC credit card data
            |- esunsec.py # Module for importing E.SUN Broker export data
        |- usecases/
            |- __init__.py
            |- convert.py # Use case for converting any supported data to Beancount format, injecting specific importers
            |- refresh.py # Use case for refreshing index.bean file
        |- cli.py # Entry point for the command-line interface
|- tests/
    |- test_importers/
        |- test_hsbc_credit_card.py # Tests for HSBC credit card importer
        |- test_esunsec.py # Tests for E.SUN Broker importer
|- docs/
    |- features/
        |- import_hsbc_credit_card.md # Feature documentation for HSBC credit card import
        |- import_esunsec.md # Feature documentation for E.SUN Broker import
    |- ARCHITECTURE.md # This architecture overview document
```

## Components

We following Clean Architecture principles to separate concerns and improve maintainability.

### CLI (Adapters)

The `cli.py` play as the role of the adapter that interacts with the user. It handles command-line arguments and invokes the appropriate use cases.

### Use Cases

The use cases encapsulate the core business logic of the application. Each use case corresponds to a specific functionality, such as converting HSBC credit card data or E.SUN Broker data into Beancount format.

> It should not depend on any external libraries or frameworks, ensuring that the business logic remains isolated and testable. Use dependency inversion principle to depend on abstractions rather than concrete implementations.

### Services

The `services/` is uncategorizable adapter that provides functionalities that do not fit into importers or use cases, such as managing the `index.bean` file.

If the adapter can be grouped into a specific category (e.g., importer, exporter), consider creating a dedicated module for it.
