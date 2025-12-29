"""Utility tools for demonstration purposes."""

from strands import tool


@tool
def add_numbers(a: int, b: int) -> int:
    """
    Return the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b
