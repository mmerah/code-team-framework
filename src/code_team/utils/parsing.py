"""Utilities for parsing and extracting content from text responses."""

import re


def extract_code_block(text: str, language: str = "") -> str | None:
    """
    Extracts content from the first Markdown code block.

    Args:
        text: The text to search for code blocks.
        language: If specified, looks for a language-specific block (e.g., "yaml", "markdown").

    Returns:
        The content of the first matching code block, or None if not found.
    """
    pattern = rf"```{language}\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback to any code block if language-specific one isn't found
    if language:
        match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

    return None
