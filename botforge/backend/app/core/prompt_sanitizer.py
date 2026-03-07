"""Sanitize user-generated content before injecting into LLM prompts."""


def sanitize_list(items: list[str], max_items: int = 5, max_length: int = 100) -> str:
    """Sanitize a list of user-generated strings for LLM prompt inclusion.

    Prevents prompt injection by truncating, escaping quotes, and limiting count.
    """
    sanitized = [
        item[:max_length].replace("\n", " ").replace('"', "'").strip() for item in items[:max_items]
    ]
    return ", ".join(f'"{item}"' for item in sanitized if item)


def sanitize_number(value: float, max_value: float = 1e6) -> float:
    """Clamp a number to prevent injection via extreme values."""
    return min(abs(value), max_value)
