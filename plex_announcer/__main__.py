#!/usr/bin/env python3
"""Main entry point for the Plex Discord Announcer bot."""

import asyncio
import argparse
import os
from dotenv import load_dotenv

from plex_announcer.core.discord_bot import DiscordBot
from plex_announcer.core.plex_monitor import PlexMonitor
from plex_announcer.utils.logging_config import configure_logging

async def main():
    """Run the Plex Discord Announcer bot."""
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logger = configure_logging()
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
        tv_library=tv_library
    )
    
    # Initialize and run Discord bot
    discord_token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    check_interval = int(os.getenv("CHECK_INTERVAL", "3600"))
    data_file = os.getenv("DATA_FILE", "processed_media.json")
    notify_movies = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
    notify_tv = os.getenv("NOTIFY_TV", "true").lower() == "true"
    
    if not discord_token:
        logger.error("DISCORD_TOKEN is required. Please set it in your .env file.")
        return
    
    if not channel_id:
        logger.error("CHANNEL_ID is required. Please set it in your .env file.")
        return
    
    bot = DiscordBot(
        token=discord_token,
        channel_id=int(channel_id),
        plex_monitor=plex_monitor,
        check_interval=check_interval,
        data_file=data_file,
        notify_movies=notify_movies,
        notify_tv=notify_tv
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
