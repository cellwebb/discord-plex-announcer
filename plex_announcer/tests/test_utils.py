"""Tests for utility functions."""

import pytest

from plex_announcer.utils.formatting import format_duration


def test_format_duration():
    """Test formatting duration from milliseconds to human-readable string."""
    # 1 hour and 30 minutes in milliseconds
    milliseconds = (1 * 60 * 60 + 30 * 60) * 1000
    assert format_duration(milliseconds) == "1h 30m"

    # 2 hours in milliseconds
    milliseconds = 2 * 60 * 60 * 1000
    assert format_duration(milliseconds) == "2h 0m"

    # 45 minutes in milliseconds
    milliseconds = 45 * 60 * 1000
    assert format_duration(milliseconds) == "0h 45m"
