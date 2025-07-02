"""Utilities for exception handling and compatibility."""

import sys

# ExceptionGroup is available in Python 3.11+, but we need to handle older versions
if sys.version_info >= (3, 11):
    from builtins import ExceptionGroup  # noqa: F401
else:
    # For Python < 3.11, define a basic ExceptionGroup
    class ExceptionGroup(Exception):  # type: ignore[no-redef]  # noqa: N818
        """Compatibility ExceptionGroup for Python < 3.11."""

        def __init__(self, message: str, exceptions: list[Exception]) -> None:
            super().__init__(message)
            self.exceptions = exceptions


__all__ = ["ExceptionGroup"]
