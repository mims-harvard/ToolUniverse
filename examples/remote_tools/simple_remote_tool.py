"""Minimal provider-owned tool for ``tu serve`` and relay smoke tests."""

from tooluniverse import remote_tool


@remote_tool
def add_numbers(a: float, b: float) -> dict:
    """Add two numbers on the provider's machine."""
    return {"sum": a + b}
