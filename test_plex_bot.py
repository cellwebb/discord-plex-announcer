"""
"""

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from plex_discord_bot import (
    PlexMonitor,
    format_duration,
    load_processed_movies,
    save_processed_movies,
)


class TestPlexBot(unittest.TestCase):
    """Basic tests for Plex Discord bot functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_data_file = "test_processed_media.json"

        self.sample_movies = {"movie1", "movie2", "movie3"}

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.test_data_file):
            os.remove(self.test_data_file)

    def test_format_duration(self):
        """Test formatting duration from milliseconds to human-readable string."""
        # 1 hour and 30 minutes in milliseconds
        milliseconds = (1 * 60 * 60 + 30 * 60) * 1000
        self.assertEqual(format_duration(milliseconds), "1h 30m")

        # 2 hours in milliseconds
        milliseconds = 2 * 60 * 60 * 1000
        self.assertEqual(format_duration(milliseconds), "2h 0m")

        # 45 minutes in milliseconds
        milliseconds = 45 * 60 * 1000
        self.assertEqual(format_duration(milliseconds), "0h 45m")

    def test_save_and_load_processed_movies(self):
        """Test saving and loading processed movies."""
        with patch("plex_discord_bot.DATA_FILE", self.test_data_file):
            # Save sample data
            save_processed_movies(self.sample_movies)

            # Load it back
            loaded_movies = load_processed_movies()

            # Check if data matches
            self.assertEqual(loaded_movies, self.sample_movies)

    @patch("plexapi.server.PlexServer")
    def test_plex_monitor_connect(self, mock_plex_server):
        """Test PlexMonitor connection."""
        # Set up the mock
        mock_instance = MagicMock()
        mock_plex_server.return_value = mock_instance

        # Create PlexMonitor instance
        monitor = PlexMonitor("http://test:32400", "test_token")

        # Check if connection was attempted
        mock_plex_server.assert_called_once_with("http://test:32400", "test_token")
        self.assertIsNotNone(monitor.plex)


if __name__ == "__main__":
    unittest.main()
