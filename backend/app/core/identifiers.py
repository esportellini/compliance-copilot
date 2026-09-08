"""Canonical representation shared by product and restricted-list identifiers."""

from sqlalchemy import func


def normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def normalized_identifier_expression(column):
    """Database expression equivalent to :func:`normalize_identifier`."""
    return func.upper(func.trim(column))
