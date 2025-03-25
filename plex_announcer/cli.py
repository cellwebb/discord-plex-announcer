"""
Command-line interface for Plex Discord Announcer.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

from plex_announcer.core.discord_bot import PlexDiscordBot
from plex_announcer.core.plex_monitor import PlexMonitor

logger = logging.getLogger("plex_discord_bot")


def signal_handler(sig, frame):
    """Handle termination signals for clean shutdown."""
    logger.info("Received termination signal, shutting down...")
    sys.exit(0)


async def main():
    """Main entry point for the Plex Discord bot."""
    load_dotenv()

    # Validate required environment variables
    required_vars = [
        "DISCORD_TOKEN",
        "DISCORD_CHANNEL_ID",
        "PLEX_BASE_URL",
        "PLEX_TOKEN",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    discord_token: Optional[str] = os.getenv("DISCORD_TOKEN")
    channel_id: int = int(os.getenv("DISCORD_CHANNEL_ID"))
    movie_channel_id: Optional[int] = (
        int(os.getenv("DISCORD_MOVIE_CHANNEL_ID"))
        if os.getenv("DISCORD_MOVIE_CHANNEL_ID")
        else None
    )
    new_shows_channel_id: Optional[int] = (
        int(os.getenv("DISCORD_NEW_SHOWS_CHANNEL_ID"))
        if os.getenv("DISCORD_NEW_SHOWS_CHANNEL_ID")
        else None
    )
    recent_episodes_channel_id: Optional[int] = (
        int(os.getenv("DISCORD_RECENT_EPISODES_CHANNEL_ID"))
        if os.getenv("DISCORD_RECENT_EPISODES_CHANNEL_ID")
        else None
    )
    plex_url: str = os.getenv("PLEX_BASE_URL")
    plex_token: Optional[str] = os.getenv("PLEX_TOKEN")
    check_interval: int = int(os.getenv("CHECK_INTERVAL", "3600"))
    movie_library: str = os.getenv("PLEX_MOVIE_LIBRARY", "Movies")
    tv_library: str = os.getenv("PLEX_TV_LIBRARY", "TV Shows")
    log_level: str = os.getenv("LOGGING_LEVEL", "INFO")
    data_file: str = os.getenv("DATA_FILE", "processed_media.json")
    notify_movies: bool = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
    notify_new_shows: bool = os.getenv("NOTIFY_NEW_SHOWS", "true").lower() == "true"
    notify_recent_episodes: bool = (
        os.getenv("NOTIFY_RECENT_EPISODES", "true").lower() == "true"
    )
    recent_episode_days: int = int(os.getenv("RECENT_EPISODE_DAYS", "30"))
    plex_connect_retry: int = int(os.getenv("PLEX_CONNECT_RETRY", "3"))
    bot_presence_channel_id: Optional[int] = (
        int(os.getenv("DISCORD_BOT_PRESENCE_CHANNEL_ID"))
        if os.getenv("DISCORD_BOT_PRESENCE_CHANNEL_ID")
        else None
    )

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("plex_discord_bot.log"), logging.StreamHandler()],
    )

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(f"Connecting to Plex server at {plex_url}")
    plex_monitor = PlexMonitor(
        base_url=plex_url,
        token=plex_token,
        connect_retry=plex_connect_retry,
    )

    if not plex_monitor.plex:
        logger.error("Failed to connect to Plex. Exiting.")
        sys.exit(1)
    logger.info("Setting up Discord bot")
    logger.info(f"Default channel ID: {channel_id}")
    if movie_channel_id:
        logger.info(f"Movie channel ID: {movie_channel_id}")
    if new_shows_channel_id:
        logger.info(f"New shows channel ID: {new_shows_channel_id}")
    if recent_episodes_channel_id:
        logger.info(f"Recent episodes channel ID: {recent_episodes_channel_id}")

    bot = PlexDiscordBot(
        token=discord_token,
        channel_id=channel_id,
        plex_monitor=plex_monitor,
        movie_library=movie_library,
        tv_library=tv_library,
        notify_movies=notify_movies,
        notify_new_shows=notify_new_shows,
        notify_recent_episodes=notify_recent_episodes,
        recent_episode_days=recent_episode_days,
        check_interval=check_interval,
        data_file=data_file,
        movie_channel_id=movie_channel_id,
        new_shows_channel_id=new_shows_channel_id,
        recent_episodes_channel_id=recent_episodes_channel_id,
        bot_presence_channel_id=bot_presence_channel_id,
    )

    logger.info("Starting Discord bot")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
