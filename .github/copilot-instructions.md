<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

This is a Python library project.  
Please generate code that is modular, testable, and suitable for import and use in other scripts or applications.

**General Coding Standards and Best Practices:**

- Use type hints for all public functions, methods, and class attributes.
- Write clear, concise, and complete docstrings for all public modules, classes, and functions, following PEP 257.
- Use consistent naming conventions (PEP 8 for variables, functions, classes, and constants).
- Avoid global state; prefer instance attributes or function arguments.
- Ensure all code is modular and easily testable.
- Prefer dependency injection over hardcoded dependencies.
- Validate all user and function input; raise appropriate exceptions on error.
- Use custom exceptions for error handling where appropriate.
- All public APIs should be safe for use in asynchronous or multi-threaded contexts where applicable.
- When writing asynchronous code, clearly document async/await requirements in docstrings and usage examples.
- Provide usage examples in docstrings and in the README for all major features.
- Ensure all new code is covered by unit tests in the `tests/` directory.
- When integrating with hardware or external services, abstract access for easier testing and mocking.
- Follow the existing project structure and module boundaries.
- Prefer explicit over implicit; avoid magic values and document all constants.
- All code should be compatible with Python 3.10+ or the project's specified minimum version.

**Documentation:**
- Update README.md and module-level docstrings to reflect any new features or changes.
- Document all async APIs and provide clear usage patterns.

**Examples:**
- Place real-world usage scenarios in the `examples/` directory.
- Examples should demonstrate integration of major modules, including asynchronous usage and callback registration if relevant.

**Testing:**
- All new features and bugfixes must include or update unit tests.
- Use `coverage.py` to ensure high test coverage.
- Mock hardware, network, or external dependencies in tests.

**Formatting and Linting:**
- Code must pass `ruff` and `mypy` checks.
- Format code with `ruff format`.
- Keep line length ≤ 100 characters.

For more, see the README.md and CONTRIBUTING.md.