"""Tests for Plex monitor functionality."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from plex_announcer.core.plex_monitor import PlexMonitor


@pytest.fixture
def mock_plex_server():
    """Fixture for mocked PlexServer."""
    with patch("plex_announcer.core.plex_monitor.PlexServer") as mock_server:
        mock_instance = MagicMock()
        mock_server.return_value = mock_instance
        yield mock_server, mock_instance


def test_plex_monitor_connect(mock_plex_server):
    """Test PlexMonitor connection."""
    _, _ = mock_plex_server
    monitor = PlexMonitor("http://test:32400", "test_token")
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

    # Set up mock library and episode
    mock_library = MagicMock()
    mock_episode = MagicMock()

    # Essential fields needed by the PlexMonitor.get_recently_added_episodes method
    mock_episode.key = "/library/metadata/12345"
    mock_episode.title = "Test Episode"
    mock_episode.grandparentTitle = "Test Show"
    mock_episode.seasonNumber = 1
    mock_episode.index = 1
    mock_episode.addedAt = datetime.now()
    mock_episode.summary = "A test episode summary"
    mock_episode.thumb = "/thumb/path"
    mock_episode.grandparentThumb = "/show/thumb/path"
    mock_episode.duration = 1800000  # 30 minutes in ms

    # Configure library search to return our mock episode
    mock_library.searchEpisodes.return_value = [mock_episode]
    mock_instance.library.section.return_value = mock_library

    monitor = PlexMonitor("http://test:32400", "test_token")
    episodes = monitor.get_recently_added_episodes("TV Shows")

    assert len(episodes) == 1
    assert episodes[0]["title"] == "Test Episode"
    assert episodes[0]["show_title"] == "Test Show"
    assert episodes[0]["season_number"] == 1
    assert episodes[0]["episode_number"] == 1


def test_plex_monitor_get_recently_added_movies_no_library(mock_plex_server):
    """Test getting movies when library doesn't exist."""
    _, mock_instance = mock_plex_server

    # Set up mock with no library
    mock_instance.library.section.return_value = None

    monitor = PlexMonitor("http://test:32400", "test_token")
    with patch.object(monitor, "get_library", return_value=None):
        movies = monitor.get_recently_added_movies("NonExistentLibrary")

    assert isinstance(movies, list)
    assert len(movies) == 0


def test_plex_monitor_get_recently_added_episodes_no_library(mock_plex_server):
    """Test getting episodes when library doesn't exist."""
    _, _ = mock_plex_server

    monitor = PlexMonitor("http://test:32400", "test_token")
    with patch.object(monitor, "get_library", return_value=None):
        episodes = monitor.get_recently_added_episodes("NonExistentLibrary")

    assert isinstance(episodes, list)
    assert len(episodes) == 0
