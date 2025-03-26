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
    """Run the Plex Discord bot."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Load config
        load_dotenv()
        config = Config.from_env()

        # Configure logging
        configure_logging(log_file="plex_discord_bot.log")

        # Connect to Plex server with timeout
        logger.info(f"Connecting to Plex server at {config.plex_base_url}")
        plex_monitor = PlexMonitor(
            base_url=config.plex_base_url,
            token=config.plex_token,
            movie_library=config.movie_library,
            tv_library=config.tv_library,
            connect_retry=config.plex_connect_retry,
        )

        if not plex_monitor.plex:
            logger.warning(
                "Failed to connect to Plex. Bot will start but with limited functionality."
            )
            # Continue execution, don't exit

        # Set up Discord bot
        logger.info("Setting up Discord bot")
        logger.info(f"Movie channel ID: {config.movie_channel_id}")
        logger.info(f"New shows channel ID: {config.new_shows_channel_id}")
        logger.info(f"Recent episodes channel ID: {config.recent_episodes_channel_id}")
        logger.info(f"Bot debug channel ID: {config.bot_debug_channel_id}")

        bot = PlexDiscordBot(
            token=config.discord_token,
            plex_monitor=plex_monitor,
            movie_channel_id=config.movie_channel_id,
            new_shows_channel_id=config.new_shows_channel_id,
            recent_episodes_channel_id=config.recent_episodes_channel_id,
            bot_debug_channel_id=config.bot_debug_channel_id,
            movie_library=config.movie_library,
            tv_library=config.tv_library,
            notify_movies=config.notify_movies,
            notify_new_shows=config.notify_new_shows,
            notify_recent_episodes=config.notify_recent_episodes,
            recent_episode_days=config.recent_episode_days,
            check_interval=config.check_interval,
            webhook_enabled=config.webhook_enabled,
            webhook_port=config.webhook_port,
            webhook_host=config.webhook_host,
        )

        logger.info("Starting Discord bot")

        # Run with a timeout to prevent hanging
        try:
            await asyncio.wait_for(bot.run(), timeout=60)
        except asyncio.TimeoutError:
            logger.error("Bot startup timed out after 60 seconds. Exiting.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
