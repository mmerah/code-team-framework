"""Unit tests for parsing utilities."""

from code_team.utils.parsing import extract_code_block


class TestExtractCodeBlock:
    """Test the extract_code_block function."""

    def test_extract_simple_code_block(self) -> None:
        """Test extracting a simple code block."""
        text = """Some text before
```
def hello():
    print("Hello World")
```
Some text after"""
        result = extract_code_block(text)
        assert result == 'def hello():\n    print("Hello World")'

    def test_extract_language_specific_block(self) -> None:
        """Test extracting a language-specific code block."""
        text = """```python
def greet(name):
    return f"Hello, {name}!"
```"""
        result = extract_code_block(text, "python")
        assert result == 'def greet(name):\n    return f"Hello, {name}!"'

    def test_extract_yaml_block(self) -> None:
        """Test extracting a YAML code block."""
        text = """```yaml
version: 1.0
name: test
config:
  debug: true
```"""
        result = extract_code_block(text, "yaml")
        expected = "version: 1.0\nname: test\nconfig:\n  debug: true"
        assert result == expected

    def test_no_code_block_found(self) -> None:
        """Test when no code block is found."""
        text = "This is just plain text with no code blocks"
        assert extract_code_block(text) is None

    def test_no_matching_language_block(self) -> None:
        """Test behavior when requested language doesn't match any blocks."""
        text = """```python
print("Python code")
```"""
        result = extract_code_block(text, "javascript")
        # Should return None since there's no javascript block and no generic blocks
        assert result is None

    def test_multiple_blocks_returns_first(self) -> None:
        """Test that only the first code block is returned."""
        text = """```
First block
```
Some text
```
Second block
```"""
        result = extract_code_block(text)
        assert result == "First block"

    def test_empty_code_block(self) -> None:
        """Test extracting an empty code block."""
        text = """```

```"""
        result = extract_code_block(text)
        assert result == ""

    def test_code_block_with_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        text = """```

some code here

```"""
        result = extract_code_block(text)
        assert result == "some code here"

    def test_language_with_extra_whitespace(self) -> None:
        """Test that language specification must be exact."""
        text = """```  python
print("test")
```"""
        result = extract_code_block(text, "python")
        assert result is None

    def test_malformed_code_block(self) -> None:
        """Test handling of malformed code blocks."""
        text = """```
This block is not closed"""
        assert extract_code_block(text) is None

        text = """```python
code here
``"""
        assert extract_code_block(text, "python") is None

    def test_nested_code_markers(self) -> None:
        """Test regex behavior with nested code markers."""
        text = """```markdown
This is a markdown block with nested code:
```python
print("nested")
```
```"""
        result = extract_code_block(text, "markdown")
        assert result == "This is a markdown block with nested code:"

    def test_mixed_content_language_specific_first(self) -> None:
        """Test behavior when both language-specific and generic blocks exist."""
        text = """```
generic code block
```
```python
def specific_function():
    return True
```"""
        result = extract_code_block(text, "python")
        assert result == "def specific_function():\n    return True"

    def test_mixed_content_fallback_to_generic(self) -> None:
        """Test fallback to generic when language-specific doesn't exist."""
        text = """```
generic code block
```
```python
python_specific_code()
```"""
        result = extract_code_block(text, "javascript")
        assert result == "generic code block"

    def test_fallback_behavior_with_only_language_specific(self) -> None:
        """Test that fallback doesn't occur when only language-specific blocks exist."""
        text = """```python
print("Python code")
```"""
        result = extract_code_block(text, "javascript")
        # Should return None since there's no javascript block and no generic blocks
        assert result is None

    def test_mixed_content_generic_only(self) -> None:
        """Test behavior with mixed content when no language specified."""
        text = """```python
python_code()
```
```
generic code
```
```javascript
js_code()
```"""
        result = extract_code_block(text)
        # Should return first generic block (no language specified)
        assert result == "generic code"

    def test_language_case_sensitivity(self) -> None:
        """Test that language matching is case-sensitive."""
        text = """```Python
print("case test")
```"""
        # Should not match different case
        result = extract_code_block(text, "python")
        assert result is None

        # Should match exact case
        result = extract_code_block(text, "Python")
        assert result == 'print("case test")'

    def test_parameter_validation_empty_text(self) -> None:
        """Test handling of empty text parameter."""
        # Test with empty string instead of None
        result = extract_code_block("", "python")
        assert result is None

    def test_parameter_validation_empty_language(self) -> None:
        """Test handling of empty language parameter."""
        text = """```
test code
```"""
        # Test with empty string (which is the default)
        result = extract_code_block(text, "")
        assert result == "test code"

    def test_comprehensive_malformed_blocks(self) -> None:
        """Test various malformed code block scenarios."""
        # Missing closing backticks
        text1 = """```python
code without end"""
        assert extract_code_block(text1, "python") is None

        # Wrong number of opening backticks
        text2 = """``python
code here
```"""
        assert extract_code_block(text2, "python") is None

        # Wrong number of closing backticks
        text3 = """```python
code here
````"""
        assert extract_code_block(text3, "python") is None

        # Missing newline after language
        text4 = """```python code here```"""
        assert extract_code_block(text4, "python") is None

    def test_priority_language_specific_over_generic(self) -> None:
        """Test that language-specific blocks have priority over generic ones."""
        text = """```
generic first
```
```python
specific second
```
More text
```
generic third
```"""
        # When asking for python, should get the python-specific one
        result = extract_code_block(text, "python")
        assert result == "specific second"

        # When not specifying language, should get first generic one
        result = extract_code_block(text)
        assert result == "generic first"

    def test_empty_language_parameter(self) -> None:
        """Test that empty string for language works like no language specified."""
        text = """```python
python_code()
```
```
generic_code()
```"""
        result_empty = extract_code_block(text, "")
        result_none = extract_code_block(text)
        # Both should return the first generic block
        assert result_empty == result_none == "generic_code()"

    def test_whitespace_handling_in_blocks(self) -> None:
        """Test various whitespace scenarios within code blocks."""
        text = """```python
    # Indented code
    def test():
        return "value"

    # Another line
```"""
        result = extract_code_block(text, "python")
        expected = '# Indented code\n    def test():\n        return "value"\n\n    # Another line'
        assert result == expected

    def test_special_characters_in_language(self) -> None:
        """Test language identifiers with special characters."""
        text = """```c++
int main() {
    return 0;
}
```"""
        result = extract_code_block(text, "c++")
        assert result == "int main() {\n    return 0;\n}"

        # Test with shell/bash
        text2 = """```bash
#!/bin/bash
echo "Hello"
```"""
        result2 = extract_code_block(text2, "bash")
        assert result2 == '#!/bin/bash\necho "Hello"'
