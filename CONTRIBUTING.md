# Contributing to APRS Rover Utilities

Thank you for considering contributing to the APRS Rover Utilities project!  
We welcome contributions of all kinds, including bug reports, feature requests, code improvements, documentation, and tests.

## How to Contribute

### 1. Fork and Clone

- Fork this repository to your own GitHub account.
- Clone your fork to your local machine.

### 2. Create a Branch

- Create a new branch for your feature or bugfix:
  ```
  git checkout -b my-feature
  ```

### 3. Make Your Changes

- Follow Python best practices:
  - Use type hints for all public functions and methods.
  - Write clear and concise docstrings.
  - Use consistent naming conventions.
  - Avoid global state where possible.
  - Keep code modular and testable.
- Add or update unit tests in the `tests/` directory.
- Update documentation as needed.

### 4. Run Tests and Checks

- Run all tests:
  ```
  python -m unittest discover -s tests
  ```
- Check type hints:
  ```
  mypy src/
  ```
- Lint your code:
  ```
  ruff check src/
  ```
- (Optional) Check test coverage:
  ```
  coverage run -m unittest discover -s tests
  coverage report -m
  ```

### 5. Commit and Push

- Commit your changes with a clear message.
- Push your branch to your fork.

### 6. Open a Pull Request

- Open a pull request (PR) from your branch to the `main` branch of this repository.
- Describe your changes and reference any related issues.

## Code of Conduct

Please be respectful and constructive in all interactions.

## Need Help?

If you have questions, open an issue or start a discussion.

Thank you for helping improve APRS Rover Utilities!