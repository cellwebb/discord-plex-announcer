"""Healthcheck utilities for Plex Discord Announcer."""

import asyncio
import os
from datetime import datetime

import discord
from plexapi.server import PlexServer

from plex_announcer.utils.logging_config import configure_logging

logger = configure_logging(log_file="healthcheck.log")


async def check_discord_connection(token):
    """
    Check if we can connect to Discord.

    Args:
        token (str): Discord bot token.

    Returns:
        bool: True if connection is successful, False otherwise.
    """
    if not token:
        logger.error("Discord token not provided")
        return False

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    try:
        # Connect to Discord
        await client.login(token)
        logger.info("Successfully connected to Discord")
        await client.close()
        return True
    except discord.errors.LoginFailure:
        logger.error("Failed to connect to Discord: Invalid token")
        return False
    except Exception as e:
        logger.error(f"Failed to connect to Discord: {e}")
        return False


def check_plex_connection(url, token):
    """
    Check if we can connect to Plex.

    Args:
        url (str): Plex server URL.
        token (str): Plex authentication token.

    Returns:
        bool: True if connection is successful, False otherwise.
    """
    if not url or not token:
        logger.error("Plex URL or token not provided")
        return False

    try:
        # Connect to Plex
        PlexServer(url, token)
        logger.info("Successfully connected to Plex")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Plex: {e}")
        return False


def check_data_file(data_file):
    """
    Check if the data file is accessible and valid.

    Args:
        data_file (str): Path to the data file.

    Returns:
        bool: True if the file is accessible, False otherwise.
    """
    try:
        if os.path.exists(data_file):
            # Check if the file is readable
            with open(data_file, "r") as f:
                f.read()

            # Check modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(data_file))
            now = datetime.now()
            age_hours = (now - mod_time).total_seconds() / 3600

            logger.info(f"Data file last modified {age_hours:.1f} hours ago")
            return True
        else:
            logger.warning(f"Data file {data_file} does not exist yet")
            return True  # Not an error, file might be created later
    except Exception as e:
        logger.error(f"Error accessing data file: {e}")
        return False


async def run_healthcheck():
    """Run all healthchecks and return overall status."""
    from dotenv import load_dotenv

    load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN")
    plex_base_url = os.getenv("PLEX_BASE_URL", "http://localhost:32400")
    plex_token = os.getenv("PLEX_TOKEN")
    data_file = os.getenv("DATA_FILE", "processed_media.json")

    logger.info("Starting healthcheck")

    discord_ok = await check_discord_connection(discord_token)
    plex_ok = check_plex_connection(plex_base_url, plex_token)
    data_ok = check_data_file(data_file)

    all_ok = discord_ok and plex_ok and data_ok

    if all_ok:
        logger.info("All healthchecks passed")
    else:
        logger.error("Some healthchecks failed")

    return all_ok


if __name__ == "__main__":
    asyncio.run(run_healthcheck())
