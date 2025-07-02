"""Utilities for parsing and extracting content from text responses."""

import re


def extract_code_block(text: str, language: str = "") -> str | None:
    """
    Extracts content from the first Markdown code block.

    When a language is specified, it first looks for a language-specific block
    with exact matching. If no exact match is found, it falls back to any
    code block (both generic and language-specific).
    When no language is specified, it returns the first generic code block found.

    Args:
        text: The text to search for code blocks.
        language: If specified, looks for a language-specific block (e.g., "yaml", "python").
                 If not found, falls back to any code block.

    Returns:
        The content of the first matching code block, or None if not found.
    """
    if language:
        # Look for exact language-specific block first
        # Escape special regex characters in language and ensure exact match
        escaped_language = re.escape(language)
        pattern = rf"```{escaped_language}\n(.*?)\n```(?!`)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback to generic code blocks only (not other language-specific ones)
        # Ensure proper closing with exactly 3 backticks
        pattern = r"```([^\n]*)\n(.*?)\n```(?!`)"
        for match in re.finditer(pattern, text, re.DOTALL):
            language_part = match.group(1).strip()
            if not language_part:  # Empty language = generic block
                return match.group(2).strip()
        return None
    else:
        # No language specified, get first generic code block only
        # Find all code blocks and return first one without language
        pattern = r"```([^\n]*)\n(.*?)\n```(?!`)"
        for match in re.finditer(pattern, text, re.DOTALL):
            language_part = match.group(1).strip()
            if not language_part:  # Empty language = generic block
                return match.group(2).strip()
        return None
