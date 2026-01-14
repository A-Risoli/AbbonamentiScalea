# AGENTS.md - Guidelines for Agentic Coding

This document provides guidelines for agentic coding agents working in the Abbonamenti repository.

## Project Overview

- **Language**: Python 3.13+
- **Project Type**: Python application
- **Package Name**: abbonamenti

## Build, Lint, and Test Commands

### Linting
```bash
# Run Ruff linter (checks for code style and errors)
ruff check .

# Auto-fix issues where possible
ruff check . --fix

# Run Ruff formatter
ruff format .
```

### Testing
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_module.py

# Run a specific test function
pytest tests/test_module.py::test_function_name

# Run tests with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_pattern"

# Show code coverage
pytest --cov=abbonamenti
```

### Type Checking
```bash
# Run mypy type checker (if configured)
mypy abbonamenti
```

## Code Style Guidelines

### Imports
- Use absolute imports for internal modules: `from abbonamenti.module import Class`
- Group imports in this order: standard library, third-party, local application
- Separate each group with a blank line
- Use `isort` or Ruff's import sorting: `ruff check --select I --fix .`

### Formatting
- Use Ruff as the formatter: `ruff format .`
- Line length: 88 characters (default)
- Use double quotes for strings and docstrings
- Use f-strings for string formatting

### Type Annotations
- Use type hints for all function parameters and return values
- Use `typing` module for complex types: `from typing import List, Optional, Dict, Any`
- Use `|` syntax for unions (Python 3.10+): `str | int` instead of `Union[str, int]`
- Prefer type aliases for complex types: `UserId = int`

### Naming Conventions
- **Variables/Functions**: snake_case (`user_name`, `get_user()`)
- **Classes**: PascalCase (`UserService`, `SubscriptionManager`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `API_KEY`)
- **Private members**: single underscore prefix (`_internal_method`)

### Error Handling
- Use specific exceptions: `ValueError`, `KeyError`, `ConnectionError`
- Wrap external API calls in try-except blocks
- Always include error messages: `raise ValueError("Invalid user ID: {user_id}")`
- Use context managers for resource management: `with open("file.txt") as f:`

### Code Organization
- Keep functions under 50 lines
- Keep classes focused on single responsibility
- Use docstrings for all public functions and classes (Google style preferred)
- Place type hints on the same line for short signatures, new line for long ones

### Dependencies
- Check `pyproject.toml` for existing dependencies
- Use minimal external dependencies
- Prefer standard library solutions when possible

### Testing
- Write tests for all public functions and methods
- Use descriptive test names: `test_should_return_user_when_id_is_valid()`
- Use pytest fixtures for test setup
- Keep tests independent and fast

### Best Practices
- Write clear, self-documenting code
- Avoid premature optimization
- Use list comprehensions for simple transformations
- Use `dataclasses` or `pydantic` for data models
- Prefer composition over inheritance
- Use `pathlib` for file path operations

## Notes
- This is a new project - establish patterns early and maintain consistency
- All changes should pass linting and tests before commit
- When in doubt, prioritize readability and maintainability
