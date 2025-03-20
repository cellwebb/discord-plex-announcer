#!/usr/bin/env python3
"""
Test script to verify connections to Discord and Plex.
"""
import logging
import os
import sys

import discord
from dotenv import load_dotenv
from plexapi.exceptions import NotFound, Unauthorized
from plexapi.server import PlexServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


def test_discord_connection():
    """Test Discord API connection with the provided token."""
    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")

    if not token:
        logger.error("DISCORD_TOKEN not found in .env file")
        return False

    try:
        # Create a client and test the token by getting the application info
        client = discord.Client(intents=discord.Intents.default())

        # Use a simple callback to verify token works
        @client.event
        async def on_ready():
            logger.info(f"✅ Successfully connected to Discord as {client.user}")
            channel = None

            if channel_id and channel_id != "0":
                try:
                    channel = client.get_channel(int(channel_id))
                    if channel:
                        logger.info(f"✅ Found channel: #{channel.name}")
                    else:
                        logger.warning(f"❌ Could not find channel with ID {channel_id}")
                except ValueError:
                    logger.error(f"❌ Invalid channel ID format: {channel_id}")
            else:
                logger.warning("❌ No channel ID provided or set to 0")

            await client.close()

        # Run the client briefly just to test connection
        client.run(token)
        return True
    except discord.LoginFailure:
        logger.error("❌ Discord authentication failed: Invalid token")
        return False
    except Exception as e:
        logger.error(f"❌ Discord connection error: {e}")
        return False


def test_plex_connection():
    """Test connection to the Plex server."""
    base_url = os.getenv("PLEX_BASE_URL")
    token = os.getenv("PLEX_TOKEN")

    if not base_url:
        logger.error("PLEX_BASE_URL not found in .env file")
        return False

    if not token:
        logger.error("PLEX_TOKEN not found in .env file")
        return False

    try:
        # Connect to the Plex server
        plex = PlexServer(base_url, token)
        logger.info(f"✅ Successfully connected to Plex server: {plex.friendlyName}")

        # Test access to the Movies library
        try:
            movies = plex.library.section("Movies")
            movie_count = len(movies.all())
            logger.info(f"✅ Found Movies library with {movie_count} movies")

            # List the 5 most recently added movies
            recent_movies = movies.search(sort="addedAt:desc")[:5]
            logger.info("Recently added movies:")
            for movie in recent_movies:
                logger.info(f"  - {movie.title} ({movie.year}) - Added: {movie.addedAt}")

            return True
        except NotFound:
            logger.error("❌ Movies library not found on Plex server")
            # List available libraries
            libraries = plex.library.sections()
            logger.info("Available libraries:")
            for library in libraries:
                logger.info(f"  - {library.title} ({library.type})")
            return False
    except Unauthorized:
        logger.error("❌ Plex authentication failed: Invalid token")
        return False
    except Exception as e:
        logger.error(f"❌ Plex connection error: {e}")
        return False


if __name__ == "__main__":
    logger.info("Testing Discord and Plex connections...")

    # Test Discord
    logger.info("\n=== Testing Discord Connection ===")
    discord_ok = test_discord_connection()

    # Test Plex
    logger.info("\n=== Testing Plex Connection ===")
    plex_ok = test_plex_connection()

    # Summary
    logger.info("\n=== Connection Test Results ===")
    logger.info(f"Discord: {'✅ Connected' if discord_ok else '❌ Failed'}")
    logger.info(f"Plex: {'✅ Connected' if plex_ok else '❌ Failed'}")

    if not discord_ok or not plex_ok:
        logger.info("\nPlease update your .env file with the correct credentials and try again.")
        sys.exit(1)
    else:
        logger.info("\nAll connections successful! You're ready to run the bot.")
        sys.exit(0)
