"""Tests for utility functions."""

import json
import os
from unittest.mock import mock_open, patch

import pytest

from plex_announcer.utils.formatting import format_duration
from plex_announcer.utils.media_storage import (load_processed_media,
                                                save_processed_media)


@pytest.fixture
def test_data_file():
    """Fixture for test data file path."""
    return "test_processed_media.json"


@pytest.fixture
def sample_media():
    """Fixture for sample media data."""
    return {"movie1", "movie2", "movie3"}


@pytest.fixture(autouse=True)
def cleanup(test_data_file):
    """Cleanup test files after tests."""
    yield
    if os.path.exists(test_data_file):
        os.remove(test_data_file)


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


def test_save_and_load_processed_media(test_data_file, sample_media):
    """Test saving and loading processed media."""
    # Save sample data
    save_processed_media(sample_media, test_data_file)

    # Load it back
    loaded_media = load_processed_media(test_data_file)

    # Check if data matches
    assert loaded_media == sample_media


def test_load_processed_media_no_file(test_data_file):
    """Test loading processed media when file doesn't exist."""
    # Make sure file doesn't exist
    if os.path.exists(test_data_file):
        os.remove(test_data_file)

    # Load from non-existent file should return empty set
    loaded_media = load_processed_media(test_data_file)
    assert loaded_media == set()


def test_load_processed_media_with_error():
    """Test loading processed media with file read error."""
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = IOError("Mock IO Error")
        loaded_media = load_processed_media("dummy.json")
        assert loaded_media == set()


def test_save_processed_media_with_error(sample_media):
    """Test saving processed media with file write error."""
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = IOError("Mock IO Error")
        # Should not raise exception but log error
        save_processed_media(sample_media, "dummy.json")
