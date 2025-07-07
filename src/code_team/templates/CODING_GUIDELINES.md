# Coding Guidelines

## Introduction
These guidelines define the specific rules and standards for writing code in this project. Adherence to these rules ensures consistency, readability, and quality across the entire codebase. All submitted code must comply with these standards.

## 1. Testing

-   **Test-First Approach**: All new functionality must be accompanied by tests. For bug fixes, a regression test must be written first to prove the existence of the bug, and it must pass after the fix is applied.
-   **Framework**: We use `pytest` as our testing framework.
-   **Location**: Tests must be placed in the `tests/` directory, mirroring the structure of the `src/` directory. For example, tests for `src/code_team/utils/filesystem.py` should be in `tests/utils/test_filesystem.py`.
-   **Coverage**: Strive for high test coverage. Every logical path in your code should be exercised by at least one test case.
-   **Assertions**: Use descriptive assertion messages where necessary to make test failures easier to debug.

## 2. Linting and Formatting

-   **Tooling**: We enforce code style and quality using `ruff`.
-   **Mandatory Checks**: Before work on a task is considered complete, the code MUST pass both of the following checks without errors:
    1.  `ruff format --check .`
    2.  `ruff check .`
-   **Automation**: These checks are run automatically during the `VERIFYING` state. Failure to pass will result in the task being rejected.

## 3. Error Handling

-   **Specific Exceptions**: Avoid using the generic `Exception`. Define and use custom, specific exception classes where appropriate (e.g., `UserNotFoundError` instead of `ValueError`).
-   **Catch Specific Errors**: Do not use broad `except Exception:` or bare `except:` clauses. Catch only the specific exceptions you expect and know how to handle.
-   **No Silent Failures**: Do not swallow exceptions. If you catch an exception, either handle it completely, re-raise it, or wrap it in a custom exception. Always log errors with sufficient context.

## 4. Comments and Docstrings

-   **Docstrings**: All public modules, classes, and functions MUST have a docstring. Follow the Google Python Style Guide for formatting. Docstrings should explain the purpose of the code, its arguments, and what it returns.
    ```python
    def get_user(user_id: int) -> User:
        """Retrieves a user from the database by their ID.

        Args:
            user_id: The unique identifier for the user.

        Returns:
            The User object if found.

        Raises:
            UserNotFoundError: If no user with the given ID exists.
        """
    ```
-   **Inline Comments**: Use inline comments (`#`) sparingly. They should explain the *why*, not the *what*. The code itself should be clear enough to explain what it is doing. Use comments for complex business logic, workarounds, or algorithm explanations.

## 5. Security

-   **No Hardcoded Secrets**: Never commit secrets (API keys, passwords, tokens, etc.) to the repository. Use environment variables or a designated secrets management system.
-   **Input Sanitization**: All input from external sources (e.g., API requests, file contents) MUST be sanitized and validated before use to prevent injection attacks.
-   **Dependency Management**: Use a tool like `pip-audit` or `Snyk` to check for vulnerabilities in dependencies. All new dependencies must be approved.