"""
Configuration management for Plex Discord Announcer.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration settings for the Plex Discord Announcer."""

    discord_token: str
    movie_channel_id: int
    new_shows_channel_id: int
    recent_episodes_channel_id: int
    bot_debug_channel_id: int
    plex_base_url: str
    plex_token: str
    check_interval: int = 3600
    movie_library: str = "Movies"
    tv_library: str = "TV Shows"
    log_level: str = "INFO"
    notify_movies: bool = True
    notify_new_shows: bool = True
    notify_recent_episodes: bool = True
    recent_episode_days: int = 30
    plex_connect_retry: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance from environment variables."""
        # Validate required environment variables
        required_vars = [
            "DISCORD_TOKEN",
            "DISCORD_MOVIE_CHANNEL_ID",
            "DISCORD_NEW_SHOWS_CHANNEL_ID",
            "DISCORD_RECENT_EPISODES_CHANNEL_ID",
            "DISCORD_BOT_DEBUG_CHANNEL_ID",
            "PLEX_BASE_URL",
            "PLEX_TOKEN",
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Parse channel IDs
        movie_channel_id = int(os.getenv("DISCORD_MOVIE_CHANNEL_ID"))
        new_shows_channel_id = int(os.getenv("DISCORD_NEW_SHOWS_CHANNEL_ID"))
        recent_episodes_channel_id = int(os.getenv("DISCORD_RECENT_EPISODES_CHANNEL_ID"))
        bot_debug_channel_id = int(os.getenv("DISCORD_BOT_DEBUG_CHANNEL_ID"))

        # Parse boolean flags
        notify_movies = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
        notify_new_shows = os.getenv("NOTIFY_NEW_SHOWS", "true").lower() == "true"
        notify_recent_episodes = os.getenv("NOTIFY_RECENT_EPISODES", "true").lower() == "true"

        return cls(
            discord_token=os.getenv("DISCORD_TOKEN"),
            movie_channel_id=movie_channel_id,
            new_shows_channel_id=new_shows_channel_id,
            recent_episodes_channel_id=recent_episodes_channel_id,
            bot_debug_channel_id=bot_debug_channel_id,
            plex_base_url=os.getenv("PLEX_BASE_URL"),
            plex_token=os.getenv("PLEX_TOKEN"),
            check_interval=int(os.getenv("CHECK_INTERVAL", "3600")),
            movie_library=os.getenv("PLEX_MOVIE_LIBRARY", "Movies"),
            tv_library=os.getenv("PLEX_TV_LIBRARY", "TV Shows"),
            log_level=os.getenv("LOGGING_LEVEL", "INFO"),
            notify_movies=notify_movies,
            notify_new_shows=notify_new_shows,
            notify_recent_episodes=notify_recent_episodes,
            recent_episode_days=int(os.getenv("RECENT_EPISODE_DAYS", "30")),
            plex_connect_retry=int(os.getenv("PLEX_CONNECT_RETRY", "3")),
        )
