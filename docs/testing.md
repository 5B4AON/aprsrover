# Testing Guide

## Overview
This project is designed for high testability, with all hardware access abstracted and comprehensive unit tests provided.

## Running Tests
Run all unit tests:
```sh
python3 -m unittest discover -s tests
```

Run tests with coverage:
```sh
coverage run -m unittest discover -s tests
coverage report -m
```

Generate an HTML coverage report:
```sh
coverage html
```
Open `htmlcov/index.html` in your browser to view detailed coverage.

## Type Checking
Run mypy for static type checking:
```sh
mypy src/
```

## Linting
Run Ruff for linting:
```sh
ruff check src/
```

Auto-format code with Ruff:
```sh
ruff format src/
```

