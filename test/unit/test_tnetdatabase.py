"""Unit tests for database module."""
#   import json
#   import os
#   import sys
#   import signal
#   import logging
#   from functools import wraps
#   import pytest
from tnetserver import tnetdatabase


def test_simple_mocking(mocker):
    """Hello world."""
    mock_db_service = mocker.patch(
        "other_code.services.db_service",
        autospec=True)

    mock_data = [(0, "fake row", 0.0)]

    mock_db_service.return_value = mock_data

    print("\n(Calling count_service with the DB mocked out...)")

#   count_service("foo")
    c = 1

    mock_db_service.assert_called_with("foo")

    print('yes')
    assert c == 1


def test_db_set_invalid_path():
    """Test db path."""
    assert tnetdatabase.db_initialise('/fake/path') is False
