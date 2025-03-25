"""
Command-line interface for Plex Discord Announcer.
"""

import asyncio
import logging
import signal
import sys

from dotenv import load_dotenv

from plex_announcer.core.discord_bot import PlexDiscordBot
from plex_announcer.core.plex_monitor import PlexMonitor
from plex_announcer.utils.config import Config
from plex_announcer.utils.logging_config import configure_logging

logger = logging.getLogger("plex_discord_bot")


def signal_handler(sig, frame):
    """Handle termination signals for clean shutdown."""
    logger.info("Received termination signal, shutting down...")
    sys.exit(0)


async def main():
    """Main entry point for the Plex Discord bot."""
    load_dotenv()

    try:
        # Load configuration from environment variables
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Configure logging
    configure_logging(log_file="plex_discord_bot.log")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Connect to Plex server
    logger.info(f"Connecting to Plex server at {config.plex_base_url}")
    plex_monitor = PlexMonitor(
        base_url=config.plex_base_url,
        token=config.plex_token,
        movie_library=config.movie_library,
        tv_library=config.tv_library,
        connect_retry=config.plex_connect_retry,
    )

    if not plex_monitor.plex:
        logger.error("Failed to connect to Plex. Exiting.")
        sys.exit(1)

    # Set up Discord bot
    logger.info("Setting up Discord bot")
    logger.info(f"Default channel ID: {config.channel_id}")
    if config.movie_channel_id:
        logger.info(f"Movie channel ID: {config.movie_channel_id}")
    if config.new_shows_channel_id:
        logger.info(f"New shows channel ID: {config.new_shows_channel_id}")
    if config.recent_episodes_channel_id:
        logger.info(f"Recent episodes channel ID: {config.recent_episodes_channel_id}")

    bot = PlexDiscordBot(
        token=config.discord_token,
        channel_id=config.channel_id,
        plex_monitor=plex_monitor,
        movie_library=config.movie_library,
        tv_library=config.tv_library,
        notify_movies=config.notify_movies,
        notify_new_shows=config.notify_new_shows,
        notify_recent_episodes=config.notify_recent_episodes,
        recent_episode_days=config.recent_episode_days,
        check_interval=config.check_interval,
        movie_channel_id=config.movie_channel_id,
        new_shows_channel_id=config.new_shows_channel_id,
        recent_episodes_channel_id=config.recent_episodes_channel_id,
        bot_presence_channel_id=config.bot_presence_channel_id,
    )

    logger.info("Starting Discord bot")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
