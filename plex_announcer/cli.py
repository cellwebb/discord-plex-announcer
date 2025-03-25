"""
Command-line interface for Plex Discord Announcer.
"""

import argparse
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
    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Plex Discord Bot")
    parser.add_argument("--token", help="Discord bot token")
    parser.add_argument(
        "--channel", type=int, help="Discord channel ID for notifications"
    )
    parser.add_argument(
        "--movie-channel", type=int, help="Discord channel ID for movie notifications"
    )
    parser.add_argument(
        "--new-shows-channel",
        type=int,
        help="Discord channel ID for new TV show notifications",
    )
    parser.add_argument(
        "--recent-episodes-channel",
        type=int,
        help="Discord channel ID for recent episode notifications",
    )
    parser.add_argument("--plex-url", help="Plex server URL")
    parser.add_argument("--plex-token", help="Plex authentication token")
    parser.add_argument("--interval", type=int, help="Check interval in seconds")
    parser.add_argument("--movie-lib", help="Movie library name")
    parser.add_argument("--tv-lib", help="TV library name")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    parser.add_argument(
        "--data-file", help="Path to data file for storing processed media"
    )
    args = parser.parse_args()

    # Configure with environment variables or command-line args
    discord_token: Optional[str] = args.token or os.getenv("DISCORD_TOKEN")
    channel_id: int = args.channel or int(os.getenv("CHANNEL_ID", "0"))
    movie_channel_id: Optional[int] = args.movie_channel or (
        int(os.getenv("MOVIE_CHANNEL_ID")) if os.getenv("MOVIE_CHANNEL_ID") else None
    )
    new_shows_channel_id: Optional[int] = args.new_shows_channel or (
        int(os.getenv("NEW_SHOWS_CHANNEL_ID"))
        if os.getenv("NEW_SHOWS_CHANNEL_ID")
        else None
    )
    recent_episodes_channel_id: Optional[int] = args.recent_episodes_channel or (
        int(os.getenv("RECENT_EPISODES_CHANNEL_ID"))
        if os.getenv("RECENT_EPISODES_CHANNEL_ID")
        else None
    )
    plex_url: str = args.plex_url or os.getenv("PLEX_URL", "http://localhost:32400")
    plex_token: Optional[str] = args.plex_token or os.getenv("PLEX_TOKEN")
    check_interval: int = args.interval or int(os.getenv("CHECK_INTERVAL", "3600"))
    movie_library: str = args.movie_lib or os.getenv("MOVIE_LIBRARY", "Movies")
    tv_library: str = args.tv_lib or os.getenv("TV_LIBRARY", "TV Shows")
    log_level: str = args.log_level or os.getenv("LOGGING_LEVEL", "INFO")
    data_file: str = args.data_file or os.getenv("DATA_FILE", "processed_media.json")
    notify_movies: bool = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
    notify_new_shows: bool = os.getenv("NOTIFY_NEW_SHOWS", "true").lower() == "true"
    notify_recent_episodes: bool = (
        os.getenv("NOTIFY_RECENT_EPISODES", "true").lower() == "true"
    )
    recent_episode_days: int = int(os.getenv("RECENT_EPISODE_DAYS", "30"))
    plex_connect_retry: int = int(os.getenv("PLEX_CONNECT_RETRY", "3"))

    # Validate required parameters
    if not discord_token:
        print(
            "Error: Discord token not provided. Set DISCORD_TOKEN env var or use --token"
        )
        sys.exit(1)

    if not plex_token:
        print(
            "Error: Plex token not provided. Set PLEX_TOKEN env var or use --plex-token"
        )
        sys.exit(1)

    if channel_id == 0:
        print(
            "Error: Discord channel ID not provided. Set CHANNEL_ID env var or use --channel"
        )
        sys.exit(1)

    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("plex_discord_bot.log"), logging.StreamHandler()],
    )

    # Configure signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set up Plex monitor
    logger.info(f"Connecting to Plex server at {plex_url}")
    plex_monitor = PlexMonitor(
        base_url=plex_url,
        token=plex_token,
        connect_retry=plex_connect_retry,
    )

    # Check Plex connection
    if not plex_monitor.plex:
        logger.error("Failed to connect to Plex. Exiting.")
        sys.exit(1)

    # Set up Discord bot
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
    )

    logger.info("Starting Discord bot")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
