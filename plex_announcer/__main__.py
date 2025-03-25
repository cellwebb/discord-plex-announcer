#!/usr/bin/env python3
"""Main entry point for the Plex Discord Announcer bot."""

import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

from plex_announcer.core.discord_bot import DiscordBot
from plex_announcer.core.plex_monitor import PlexMonitor


def setup_logging():
    """Set up logging configuration."""
    log_level = os.getenv("LOGGING_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Ensure logs directory exists
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, "plex_announcer.log")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )

    # Set log level for other libraries
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("plexapi").setLevel(logging.WARNING)


async def main():
    """Run the Plex Discord Announcer bot."""
    # Load environment variables
    load_dotenv()

    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Plex Discord Announcer")

    # Initialize Plex monitor
    plex_url = os.getenv("PLEX_URL", "http://localhost:32400")
    plex_token = os.getenv("PLEX_TOKEN")
    movie_library = os.getenv("MOVIE_LIBRARY", "Movies")
    tv_library = os.getenv("TV_LIBRARY", "TV Shows")

    if not plex_token:
        logger.error("PLEX_TOKEN is required. Please set it in your .env file.")
        return

    plex_monitor = PlexMonitor(
        base_url=plex_url,
        token=plex_token,
        movie_library=movie_library,
        tv_library=tv_library,
    )

    # Initialize and run Discord bot
    discord_token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    check_interval = int(os.getenv("CHECK_INTERVAL", "3600"))
    data_file = os.getenv("DATA_FILE", "data/processed_media.json")
    notify_movies = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
    notify_new_shows = os.getenv("NOTIFY_NEW_SHOWS", "true").lower() == "true"
    notify_recent_episodes = (
        os.getenv("NOTIFY_RECENT_EPISODES", "true").lower() == "true"
    )
    recent_episode_days = int(os.getenv("RECENT_EPISODE_DAYS", "30"))

    if not discord_token:
        logger.error("DISCORD_TOKEN is required. Please set it in your .env file.")
        return

    if not channel_id:
        logger.error("CHANNEL_ID is required. Please set it in your .env file.")
        return

    # Ensure data directory exists
    data_dir = os.path.dirname(data_file)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Created data directory: {data_dir}")

    logger.info(
        f"Discord token: {discord_token[:5]}...{discord_token[-5:] if len(discord_token) > 10 else ''}"  # noqa: E501
    )
    logger.info(f"Channel ID: {channel_id}")
    logger.info(f"Notify Movies: {notify_movies}")
    logger.info(f"Notify New Shows: {notify_new_shows}")
    logger.info(f"Notify Recent Episodes: {notify_recent_episodes}")
    logger.info(f"Recent Episode Days: {recent_episode_days}")
    logger.info(f"Data file: {data_file}")

    bot = DiscordBot(
        token=discord_token,
        channel_id=int(channel_id),
        plex_monitor=plex_monitor,
        check_interval=check_interval,
        data_file=data_file,
        notify_movies=notify_movies,
        notify_new_shows=notify_new_shows,
        notify_recent_episodes=notify_recent_episodes,
        recent_episode_days=recent_episode_days,
    )

    try:
        logger.info(f"Bot configured to check every {check_interval} seconds")
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.exception(f"Error running bot: {e}")
    finally:
        logger.info("Bot shutting down")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plex Discord Announcer")
    parser.add_argument("--env", type=str, help="Path to .env file")
    args = parser.parse_args()

    if args.env:
        load_dotenv(args.env)

    asyncio.run(main())
