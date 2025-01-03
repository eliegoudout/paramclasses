"""Global pytest conftest."""

import pytest


@pytest.fixture
def null() -> object:
    """To avoir `null = object()` 1.765.354 times. Ruff happy now..."""
    return object()
