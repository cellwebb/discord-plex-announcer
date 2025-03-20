#!/usr/bin/env python3
"""
Discord bot that announces new movies added to a Plex server.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from plexapi.server import PlexServer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
PLEX_BASE_URL = os.getenv("PLEX_BASE_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))  # Default: check every 5 minutes


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

last_check_time = datetime.now() - timedelta(days=1)  # Start by checking movies from the last day


@bot.event
async def on_ready():
    """Event fired when the bot is ready and connected to Discord."""
    logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    if not check_for_new_movies.is_running():
        check_for_new_movies.start()


@tasks.loop(seconds=CHECK_INTERVAL)
async def check_for_new_movies():
    """
    Periodically check the Plex server for new movies and announce them
    in the specified Discord channel.
    """
    global last_check_time

    try:
        logger.info("Checking for new movies...")

        # Connect to the Plex server
        plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)

        # Get all movies added since last check
        current_time = datetime.now()
        movies = plex.library.section("Movies").search(libtype="movie", sort="addedAt:desc")

        # Filter movies added since last check
        new_movies = [movie for movie in movies if movie.addedAt > last_check_time]

        if new_movies:
            logger.info(f"Found {len(new_movies)} new movies")
            channel = bot.get_channel(DISCORD_CHANNEL_ID)

            if channel:
                for movie in new_movies:
                    # Create a rich embed for the movie
                    embed = discord.Embed(
                        title=f"New Movie Available: {movie.title}",
                        description=(
                            movie.summary[:1024] if movie.summary else "No summary available"
                        ),
                        color=discord.Color.blue(),
                    )

                    # Add movie details
                    embed.add_field(name="Year", value=movie.year, inline=True)
                    embed.add_field(
                        name="Rating",
                        value=(f"{movie.contentRating}" if movie.contentRating else "N/A"),
                        inline=True,
                    )
                    embed.add_field(
                        name="Duration",
                        value=(f"{movie.duration // 60000} min" if movie.duration else "N/A"),
                        inline=True,
                    )

                    # Add genres if available
                    if hasattr(movie, "genres") and movie.genres:
                        genres = ", ".join([genre.tag for genre in movie.genres[:5]])
                        embed.add_field(name="Genres", value=genres, inline=False)

                    # Add poster if available
                    if movie.thumbUrl:
                        embed.set_thumbnail(url=movie.thumbUrl)

                    await channel.send(embed=embed)
                    logger.info(f"Announced movie: {movie.title}")

                    # Small delay to avoid rate limits
                    await asyncio.sleep(1)
            else:
                logger.error(f"Could not find Discord channel with ID {DISCORD_CHANNEL_ID}")
        else:
            logger.info("No new movies found")

        # Update the last check time
        last_check_time = current_time

    except Exception as e:
        logger.error(f"Error checking for new movies: {e}")


@check_for_new_movies.before_loop
async def before_check():
    """Wait until the bot is ready before starting the movie check loop."""
    await bot.wait_until_ready()


@bot.command(name="check_now")
@commands.has_permissions(administrator=True)
async def check_now(ctx):
    """
    Manually triggers a check for new movies.
    Only administrators can use this command.
    """
    await ctx.send("Manually checking for new movies...")
    await check_for_new_movies()
    await ctx.send("Check complete!")


@bot.command(name="status")
async def status(ctx):
    """Report the current status of the bot and its connections."""
    try:
        # Test Plex connection
        plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
        plex_status = f"✅ Connected to {plex.friendlyName}"
        movie_count = len(plex.library.section("Movies").all())
    except Exception as e:
        plex_status = f"❌ Failed to connect to Plex: {str(e)}"
        movie_count = "Unknown"

    # Create status embed
    embed = discord.Embed(title="Plex Announcer Status", color=discord.Color.green())

    embed.add_field(name="Plex Connection", value=plex_status, inline=False)
    embed.add_field(name="Movie Count", value=str(movie_count), inline=True)
    embed.add_field(
        name="Last Check",
        value=last_check_time.strftime("%Y-%m-%d %H:%M:%S"),
        inline=True,
    )
    embed.add_field(name="Check Interval", value=f"{CHECK_INTERVAL} seconds", inline=True)

    await ctx.send(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables")
        exit(1)
    if not PLEX_BASE_URL or not PLEX_TOKEN:
        logger.error("PLEX_BASE_URL or PLEX_TOKEN not found in environment variables")
        exit(1)
    if DISCORD_CHANNEL_ID == 0:
        logger.warning("DISCORD_CHANNEL_ID not properly set, announcements will fail")

    bot.run(DISCORD_TOKEN)
