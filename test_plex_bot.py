# flake8: noqa: E402
"""
Tests for Plex Discord bot functionality
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plex_discord_bot import (
    PlexMonitor,
    format_duration,
    load_processed_movies,
    save_processed_movies,
)


@pytest.fixture
def test_data_file():
    """Fixture for test data file path."""
    return "test_processed_media.json"


@pytest.fixture
def sample_movies():
    """Fixture for sample movie data."""
    return {"movie1", "movie2", "movie3"}


@pytest.fixture(autouse=True)
def cleanup(test_data_file):
    """Cleanup test files after tests."""
    yield
    if os.path.exists(test_data_file):
        os.remove(test_data_file)


@pytest.fixture
def mock_plex_server():
    """Fixture for mocked PlexServer."""
    with patch("plex_discord_bot.PlexServer") as mock_server:
        mock_instance = MagicMock()
        mock_server.return_value = mock_instance
        yield mock_server, mock_instance


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


def test_save_and_load_processed_movies(test_data_file, sample_movies):
    """Test saving and loading processed movies."""
    with patch("plex_discord_bot.DATA_FILE", test_data_file):
        # Save sample data
        save_processed_movies(sample_movies)

        # Load it back
        loaded_movies = load_processed_movies()

        # Check if data matches
        assert loaded_movies == sample_movies


def test_load_processed_movies_no_file(test_data_file):
    """Test loading processed movies when file doesn't exist."""
    with patch("plex_discord_bot.DATA_FILE", test_data_file):
        # Make sure file doesn't exist
        if os.path.exists(test_data_file):
            os.remove(test_data_file)

        # Load from non-existent file should return empty set
        loaded_movies = load_processed_movies()
        assert loaded_movies == set()


@patch("plex_discord_bot.PlexServer")
def test_plex_monitor_connect(mock_plex_server):
    """Test PlexMonitor connection."""
    # Set up the mock
    mock_instance = MagicMock()
    mock_plex_server.return_value = mock_instance

    # Create PlexMonitor instance
    monitor = PlexMonitor("http://test:32400", "test_token")

    # Check if connection was attempted
    mock_plex_server.assert_called_once_with("http://test:32400", "test_token")
    assert monitor.plex is not None


def test_plex_monitor_connect_unauthorized(mock_plex_server):
    """Test PlexMonitor connection with unauthorized error."""
    mock_server, _ = mock_plex_server
    mock_server.side_effect = Exception("Unauthorized")

    monitor = PlexMonitor("http://test:32400", "test_token")
    assert not monitor.connect()


def test_plex_monitor_get_library(mock_plex_server):
    """Test getting a library from PlexMonitor."""
    _, mock_instance = mock_plex_server

    # Set up the mock library
    mock_library = MagicMock()
    mock_library.section.return_value = MagicMock(name="Movies")
    mock_instance.library = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    library = monitor.get_library("Movies")

    assert library is not None
    mock_library.section.assert_called_once_with("Movies")


def test_plex_monitor_get_library_not_found(mock_plex_server):
    """Test getting a non-existent library from PlexMonitor."""
    _, mock_instance = mock_plex_server

    # Set up the mock library to raise NotFound
    mock_library = MagicMock()
    mock_library.section.side_effect = Exception("NotFound")
    mock_instance.library = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    library = monitor.get_library("NonExistentLibrary")

    assert library is None


def test_get_recently_added_movies(mock_plex_server):
    """Test getting recently added movies."""
    _, mock_instance = mock_plex_server

    # Set up mock library and movies
    mock_library = MagicMock()
    mock_movie = MagicMock()
    mock_movie.key = "/library/metadata/12345"
    mock_movie.title = "Test Movie"
    mock_movie.year = 2023
    mock_movie.addedAt = datetime.now()
    mock_movie.summary = "A test movie summary"
    mock_movie.contentRating = "PG-13"
    mock_movie.rating = 8.5
    mock_movie.thumb = "/thumb/path"
    mock_movie.duration = 7200000  # 2 hours in ms

    # Set up genres, directors, and actors
    mock_genre = MagicMock()
    mock_genre.tag = "Action"
    mock_movie.genres = [mock_genre]

    mock_director = MagicMock()
    mock_director.tag = "Test Director"
    mock_movie.directors = [mock_director]

    mock_actor = MagicMock()
    mock_actor.tag = "Test Actor"
    mock_movie.roles = [mock_actor]

    # Configure library search to return our mock movie
    mock_library.search.return_value = [mock_movie]
    mock_instance.library.section.return_value = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    movies = monitor.get_recently_added_movies("Movies")

    assert len(movies) == 1
    assert movies[0]["title"] == "Test Movie"
    assert movies[0]["year"] == 2023
    assert movies[0]["genres"] == ["Action"]
    assert movies[0]["directors"] == ["Test Director"]
    assert movies[0]["actors"] == ["Test Actor"]


def test_get_recently_added_episodes(mock_plex_server):
    """Test getting recently added TV episodes."""
    _, mock_instance = mock_plex_server

    # Set up mock library and episode with all required attributes
    mock_library = MagicMock()
    mock_episode = MagicMock()

    # Essential fields needed by the PlexMonitor.get_recently_added_episodes method
    mock_episode.key = "/library/metadata/12345"
    mock_episode.title = "Test Episode"
    mock_episode.grandparentTitle = "Test Show"
    mock_episode.seasonNumber = 1
    mock_episode.parentIndex = 1
    mock_episode.index = 1
    mock_episode.addedAt = datetime.now()
    mock_episode.originallyAvailableAt = datetime.now() - timedelta(days=7)
    mock_episode.summary = "A test episode summary"
    mock_episode.thumb = "/thumb/path"
    mock_episode.grandparentThumb = "/show/thumb/path"

    # Configure library search to return our mock episode
    mock_library.searchEpisodes.return_value = [mock_episode]
    mock_instance.library.section.return_value = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    episodes = monitor.get_recently_added_episodes("TV Shows")

    assert len(episodes) == 1
    assert episodes[0]["show_title"] == "Test Show"
    assert episodes[0]["season"] == 1
    assert episodes[0]["episode"] == 1


def test_plex_monitor_get_recently_added_movies_no_library(mock_plex_server):
    """Test getting movies when library doesn't exist."""
    _, mock_instance = mock_plex_server

    # Set up the PlexMonitor to return None for get_library
    mock_library = MagicMock()
    mock_library.section.side_effect = Exception("NotFound")
    mock_instance.library = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    movies = monitor.get_recently_added_movies("NonExistentLibrary")

    # Should return empty list when library not found
    assert movies == []


def test_plex_monitor_get_recently_added_movies_exception(mock_plex_server):
    """Test getting movies when an exception occurs."""
    _, mock_instance = mock_plex_server

    # Set up the mock library to raise an exception during search
    mock_library = MagicMock()
    mock_library.search.side_effect = Exception("Search error")
    mock_instance.library.section.return_value = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    movies = monitor.get_recently_added_movies("Movies")

    # Should return empty list when exception occurs
    assert movies == []


def test_plex_monitor_get_recently_added_episodes_no_library(mock_plex_server):
    """Test getting episodes when library doesn't exist."""
    _, mock_instance = mock_plex_server

    # Set up the PlexMonitor to return None for get_library
    mock_library = MagicMock()
    mock_library.section.side_effect = Exception("NotFound")
    mock_instance.library = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    episodes = monitor.get_recently_added_episodes("NonExistentLibrary")

    # Should return empty list when library not found
    assert episodes == []


def test_plex_monitor_get_recently_added_episodes_exception(mock_plex_server):
    """Test getting episodes when an exception occurs."""
    _, mock_instance = mock_plex_server

    # Set up the mock library to raise an exception during search
    mock_library = MagicMock()
    mock_library.searchEpisodes.side_effect = Exception("Search error")
    mock_instance.library.section.return_value = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    episodes = monitor.get_recently_added_episodes("TV Shows")

    # Should return empty list when exception occurs
    assert episodes == []
