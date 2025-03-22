"""
Plex Discord Bot - Send notifications to Discord when new media is added to Plex.

This bot monitors Plex libraries for new movies and TV shows, then sends formatted
notifications to a Discord channel. It features:
- Notifications for all new movies
- Selective notifications for TV shows (recently aired or first episodes of new shows)
- Grouping of episodes from the same show to reduce notification clutter
- Rich embeds with media details, posters, and metadata

Configuration is done via environment variables or command line arguments.
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from plexapi.exceptions import NotFound, Unauthorized
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie

# Configure logging
load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
numeric_level = getattr(logging, LOGGING_LEVEL.upper(), logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("plex_discord_bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger("plex_discord_bot")

DISCORD_TOKEN: Optional[str] = os.getenv("DISCORD_TOKEN")
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
PLEX_URL: str = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN: Optional[str] = os.getenv("PLEX_TOKEN")
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "3600"))  # Default to 1 hour
MOVIE_LIBRARY: str = os.getenv("MOVIE_LIBRARY", "Movies")
TV_LIBRARY: str = os.getenv("TV_LIBRARY", "TV Shows")
NOTIFY_MOVIES: bool = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
NOTIFY_TV: bool = os.getenv("NOTIFY_TV", "true").lower() == "true"
DATA_FILE: str = os.getenv("DATA_FILE", "processed_media.json")
PLEX_CONNECT_RETRY: int = int(os.getenv("PLEX_CONNECT_RETRY", "3"))

intents: discord.Intents = discord.Intents.default()
intents.message_content = True
bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)

processed_movies: Set[str] = set()
START_TIME: float = time.time()


class PlexMonitor:
    """
    Handles connection to Plex server and retrieves information about media libraries.

    This class manages the connection to a Plex Media Server and provides methods to
    search and retrieve information about recently added movies and TV episodes.
    """

    def __init__(self, plex_url: str, plex_token: str):
        """Initialize the Plex monitor with server URL and authentication token."""
        self.plex_url: str = plex_url
        self.plex_token: str = plex_token
        self.plex: Optional[PlexServer] = None
        self.connect()

    def connect(self) -> bool:
        """Establish connection to the Plex server."""
        retry_count = 0
        max_retries = PLEX_CONNECT_RETRY

        while retry_count < max_retries:
            try:
                self.plex = PlexServer(self.plex_url, self.plex_token)
                logger.info(f"Connected to Plex server at {self.plex_url}")
                return True
            except Unauthorized as e:
                logger.error(f"Authentication failed for Plex server: {e}")
                return False
            except (ConnectionError, TimeoutError) as e:
                retry_count += 1
                wait_time = 2**retry_count
                logger.warning(
                    f"Connection to Plex failed (attempt {retry_count}/{max_retries}): {e}"
                )
                if retry_count < max_retries:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Failed to connect to Plex: {e}")
                return False

        logger.error(f"Failed to connect to Plex after {max_retries} attempts")
        return False

    def get_library(self, library_name: str) -> Optional[LibrarySection]:
        """Get a specific library section from Plex."""
        if not self.plex:
            if not self.connect():
                return None

        try:
            library = self.plex.library.section(library_name)
            logger.info(f"Found library: {library_name}")
            return library
        except NotFound:
            logger.error(f"Library '{library_name}' not found on Plex server")
            return None
        except Exception as e:
            logger.error(f"Failed to find library '{library_name}': {e}")
            return None

    def get_recently_added_movies(self, library_name: str, days: int = 1) -> List[Dict[str, Any]]:
        """Get a list of movies added to Plex within the specified time period."""
        if not self.plex:
            if not self.connect():
                return []

        try:
            library = self.get_library(library_name)
            if not library:
                return []

            cutoff_date: datetime = datetime.now() - timedelta(days=days)
            recent_movies: List[Movie] = library.search(libtype="movie", sort="addedAt:desc")

            new_movies: List[Dict[str, Any]] = []
            for movie in recent_movies:
                if movie.addedAt > cutoff_date:
                    poster_url: Optional[str] = None
                    if movie.thumb:
                        poster_url = f"{self.plex_url}{movie.thumb}?X-Plex-Token={self.plex_token}"

                    new_movies.append(
                        {
                            "type": "movie",
                            "key": movie.key,
                            "title": movie.title,
                            "year": movie.year,
                            "added_at": movie.addedAt.isoformat(),
                            "summary": movie.summary,
                            "content_rating": getattr(movie, "contentRating", "Not Rated"),
                            "rating": getattr(movie, "rating", None),
                            "poster_url": poster_url,
                            "duration": movie.duration,
                            "genres": [genre.tag for genre in getattr(movie, "genres", [])],
                            "directors": [
                                director.tag for director in getattr(movie, "directors", [])
                            ],
                            "actors": [actor.tag for actor in getattr(movie, "roles", [])][:3],
                        }
                    )
                else:
                    break

            return new_movies
        except Exception as e:
            logger.error(f"Error getting recently added movies: {e}")
            return []

    def get_recently_added_episodes(self, library_name: str, days: int = 1) -> List[Dict[str, Any]]:
        """Get a list of TV episodes added to Plex within the specified time period."""
        if not self.plex:
            if not self.connect():
                return []

        try:
            library = self.get_library(library_name)
            if not library:
                return []

            cutoff_date: datetime = datetime.now() - timedelta(days=days)
            recent_episodes: List[Episode] = library.searchEpisodes(sort="addedAt:desc")

            new_episodes: List[Dict[str, Any]] = []
            for episode in recent_episodes:
                if episode.addedAt > cutoff_date:
                    poster_url: Optional[str] = None
                    if episode.thumb:
                        poster_url = (
                            f"{self.plex_url}{episode.thumb}?X-Plex-Token={self.plex_token}"
                        )

                    show_poster_url: Optional[str] = None
                    if episode.grandparentThumb:
                        show_poster_url = f"{self.plex_url}{episode.grandparentThumb}?X-Plex-Token={self.plex_token}"  # noqa: E501

                    new_episodes.append(
                        {
                            "type": "episode",
                            "key": episode.key,
                            "show_title": episode.grandparentTitle,
                            "episode_title": episode.title,
                            "season": episode.parentIndex,
                            "episode": episode.index,
                            "added_at": episode.addedAt.isoformat(),
                            "summary": episode.summary,
                            "rating": getattr(episode, "rating", None),
                            "poster_url": poster_url,
                            "show_poster_url": show_poster_url,
                            "duration": episode.duration,
                        }
                    )
                else:
                    break

            return new_episodes
        except Exception as e:
            logger.error(f"Error getting recently added episodes: {e}")
            return []


def load_processed_movies() -> Set[str]:
    """Load the set of already processed media keys from disk."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Error loading processed media: {e}")
        return set()


def save_processed_movies(movies: Set[str]) -> None:
    """Save the set of processed media keys to disk."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(list(movies), f)
    except Exception as e:
        logger.error(f"Error saving processed media: {e}")


def format_duration(milliseconds: int) -> str:
    """Format a duration in milliseconds to a human-readable string (e.g., "2h 15m")."""
    total_seconds: int = milliseconds // 1000
    hours: int = total_seconds // 3600
    minutes: int = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"


@bot.event
async def on_ready():
    """Handler called when the Discord bot is ready and connected."""
    logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")

    # Validate channel ID
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find channel with ID {CHANNEL_ID}")
        await bot.close()
        return

    logger.info(f"Connected to Discord channel: {CHANNEL_ID}")


@bot.event
async def setup_hook():
    """Setup hook to run the initial check when the bot starts."""
    # Run an immediate check when bot starts
    await check_for_new_media()


@tasks.loop(seconds=CHECK_INTERVAL)
async def check_for_new_media() -> None:
    """
    Periodic task that checks for new media in Plex and sends Discord notifications.

    This function runs at regular intervals (defined by CHECK_INTERVAL) and:
    1. Checks for new movies and sends notifications for all of them
    2. Checks for new TV episodes, but only notifies for:
       - Recently aired episodes (last 30 days)
       - First episode of shows new to the server
    3. Groups episodes from the same show to reduce notification clutter
    """
    global processed_movies

    channel: Optional[discord.TextChannel] = bot.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find channel with ID {CHANNEL_ID}")
        return

    logger.info("Checking for new media...")

    if not PLEX_TOKEN:
        logger.error("Plex token is not set")
        return

    plex_monitor: PlexMonitor = PlexMonitor(PLEX_URL, PLEX_TOKEN)

    if NOTIFY_MOVIES:
        logger.info(f"Checking for new movies in library: {MOVIE_LIBRARY}")
        recent_movies: List[Dict[str, Any]] = plex_monitor.get_recently_added_movies(
            MOVIE_LIBRARY, days=1
        )

        for movie in recent_movies:
            movie_key: str = movie["key"]

            if movie_key in processed_movies:
                continue

            logger.info(f"Found new movie: {movie['title']} ({movie['year']})")

            embed: discord.Embed = discord.Embed(
                title=f"🎬 New Movie: {movie['title']} ({movie['year']})",
                description=movie["summary"][:2000],
                color=discord.Color.blue(),
            )

            if movie["poster_url"]:
                embed.set_thumbnail(url=movie["poster_url"])

            embed.add_field(
                name="Rating", value=str(movie["rating"]) if movie["rating"] else "N/A", inline=True
            )
            embed.add_field(name="Content Rating", value=movie["content_rating"], inline=True)
            embed.add_field(name="Duration", value=format_duration(movie["duration"]), inline=True)

            if movie["genres"]:
                embed.add_field(name="Genres", value=", ".join(movie["genres"]), inline=True)

            if movie["directors"]:
                embed.add_field(
                    name="Director(s)", value=", ".join(movie["directors"]), inline=True
                )

            if movie["actors"]:
                embed.add_field(name="Starring", value=", ".join(movie["actors"]), inline=True)

            embed.timestamp = datetime.now()
            embed.set_footer(text="Added to Plex")

            try:
                await channel.send(embed=embed)
                logger.info(f"Sent notification for movie: {movie['title']}")

                processed_movies.add(movie_key)
                save_processed_movies(processed_movies)

                time.sleep(1)
            except Exception as e:
                logger.error(f"Error sending movie notification: {e}")

    if NOTIFY_TV:
        logger.info(f"Checking for new TV episodes in library: {TV_LIBRARY}")
        recent_episodes: List[Dict[str, Any]] = plex_monitor.get_recently_added_episodes(
            TV_LIBRARY, days=1
        )

        # Group episodes by show
        episodes_by_show: Dict[str, Dict[str, Any]] = {}
        for episode in recent_episodes:
            if episode["key"] not in processed_movies:
                show_title: str = episode["show_title"]
                if show_title not in episodes_by_show:
                    episodes_by_show[show_title] = {
                        "show_poster_url": episode["show_poster_url"],
                        "episodes": [],
                    }

                episodes_by_show[show_title]["episodes"].append(
                    {
                        "title": episode["episode_title"],
                        "season": episode["season"],
                        "episode": episode["episode"],
                        "rating": episode["rating"],
                        "summary": episode["summary"],
                    }
                )

        # Send notifications for each show
        for show_title, show_data in episodes_by_show.items():
            if show_data["episodes"]:
                embed: discord.Embed = discord.Embed(
                    title=f"📺 New Episodes: {show_title}",
                    color=discord.Color.blue(),
                )

                if show_data["show_poster_url"]:
                    embed.set_thumbnail(url=show_data["show_poster_url"])

                # Add episode list
                episode_list: List[str] = []
                for episode in show_data["episodes"]:
                    episode_list.append(
                        f"• S{episode['season']:02d}E{episode['episode']:02d}: {episode['title']}"
                    )
                embed.add_field(name="Episodes", value="\n".join(episode_list), inline=False)

                embed.timestamp = datetime.now()
                embed.set_footer(text="Added to Plex")

                try:
                    await channel.send(embed=embed)
                    logger.info(f"Sent notification for show: {show_title}")

                    # Mark all episodes as processed
                    for episode in show_data["episodes"]:
                        processed_movies.add(episode["key"])
                    save_processed_movies(processed_movies)

                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error sending TV show notification: {e}")


@bot.command(name="checkplex")
async def check_plex(ctx: commands.Context) -> None:
    """
    Discord command to manually check for new media.

    This command allows Discord users to manually trigger a check for new media
    rather than waiting for the scheduled interval.
    """
    await ctx.send("Checking for new media...")
    await check_for_new_media()
    await ctx.send("Check complete!")


@bot.command(name="status")
async def status(ctx: commands.Context) -> None:
    """Discord command to display the current bot status and configuration."""
    global processed_movies

    embed: discord.Embed = discord.Embed(
        title="Plex Discord Bot Status",
        description="Current bot status and configuration",
        color=0x00FF00,
    )

    embed.add_field(name="Plex Server", value=PLEX_URL, inline=False)

    if NOTIFY_MOVIES:
        embed.add_field(name="Movie Library", value=MOVIE_LIBRARY, inline=True)
    else:
        embed.add_field(name="Movie Notifications", value="Disabled", inline=True)

    if NOTIFY_TV:
        embed.add_field(name="TV Library", value=TV_LIBRARY, inline=True)
    else:
        embed.add_field(name="TV Notifications", value="Disabled", inline=True)

    embed.add_field(name="Check Interval", value=f"{CHECK_INTERVAL} seconds", inline=True)
    embed.add_field(name="Processed Media", value=str(len(processed_movies)), inline=True)

    uptime = time.time() - START_TIME
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    embed.add_field(
        name="Bot Uptime",
        value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s",
        inline=True,
    )

    embed.timestamp = datetime.now()
    await ctx.send(embed=embed)


@bot.command(name="healthcheck")
async def healthcheck(ctx: commands.Context) -> None:
    """Check if the bot can connect to Plex and Discord."""
    embed = discord.Embed(
        title="Health Check",
        description="Checking connections to Plex and Discord...",
        color=0xFFFF00,
    )
    message = await ctx.send(embed=embed)

    plex_ok = False
    if PLEX_TOKEN:
        plex_monitor = PlexMonitor(PLEX_URL, PLEX_TOKEN)
        plex_ok = plex_monitor.plex is not None

    channel_ok = bot.get_channel(CHANNEL_ID) is not None

    embed.description = "System health status"
    embed.color = 0x00FF00 if plex_ok and channel_ok else 0xFF0000
    embed.add_field(
        name="Plex Server", value="✅ Connected" if plex_ok else "❌ Disconnected", inline=True
    )
    embed.add_field(
        name="Discord Channel",
        value="✅ Connected" if channel_ok else "❌ Disconnected",
        inline=True,
    )
    embed.add_field(
        name="Data File",
        value=(
            f"✅ Found ({len(processed_movies)} items)"
            if os.path.exists(DATA_FILE)
            else "❌ Missing"
        ),
        inline=True,
    )

    embed.timestamp = datetime.now()
    await message.edit(embed=embed)


def signal_handler(sig, frame):
    """Handle termination signals for clean shutdown."""
    logger.info("Received shutdown signal, saving data and exiting...")
    save_processed_movies(processed_movies)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main() -> None:
    """
    Main function to handle command-line arguments and starting the Discord bot.
    """
    global processed_movies, DISCORD_TOKEN, CHANNEL_ID, PLEX_URL, PLEX_TOKEN, CHECK_INTERVAL
    global MOVIE_LIBRARY, TV_LIBRARY, NOTIFY_MOVIES, NOTIFY_TV, DATA_FILE, PLEX_CONNECT_RETRY

    parser = argparse.ArgumentParser(
        description="Plex Discord Bot - Send notifications for new movies and TV episodes"
    )
    parser.add_argument("--token", help="Discord bot token")
    parser.add_argument("--channel", type=int, help="Discord channel ID for notifications")
    parser.add_argument("--plex-url", help="URL of your Plex server")
    parser.add_argument("--plex-token", help="Plex authentication token")
    parser.add_argument("--movie-library", help="Name of the Plex movie library")
    parser.add_argument("--tv-library", help="Name of the Plex TV show library")
    parser.add_argument("--notify-movies", help="Enable/disable movie notifications")
    parser.add_argument("--notify-tv", help="Enable/disable TV show notifications")
    parser.add_argument("--data-file", help="File to store processed media")
    parser.add_argument("--retry", type=int, help="Number of retries for Plex connection")
    parser.add_argument("--interval", type=int, help="Check interval in seconds")

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Set configuration from environment variables or defaults
    DISCORD_TOKEN = args.token or os.getenv("DISCORD_TOKEN")
    CHANNEL_ID = args.channel or int(os.getenv("CHANNEL_ID", "0"))
    PLEX_URL = args.plex_url or os.getenv("PLEX_URL", "http://localhost:32400")
    PLEX_TOKEN = args.plex_token or os.getenv("PLEX_TOKEN")
    CHECK_INTERVAL = args.interval or int(os.getenv("CHECK_INTERVAL", "3600"))
    MOVIE_LIBRARY = args.movie_library or os.getenv("MOVIE_LIBRARY", "Movies")
    TV_LIBRARY = args.tv_library or os.getenv("TV_LIBRARY", "TV Shows")
    NOTIFY_MOVIES = args.notify_movies or os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
    NOTIFY_TV = args.notify_tv or os.getenv("NOTIFY_TV", "true").lower() == "true"
    DATA_FILE = args.data_file or os.getenv("DATA_FILE", "processed_media.json")
    PLEX_CONNECT_RETRY = args.retry or int(os.getenv("PLEX_CONNECT_RETRY", "3"))

    # Validate required configuration
    if not DISCORD_TOKEN:
        logger.error("Discord token is required")
        sys.exit(1)
    if not CHANNEL_ID:
        logger.error("Discord channel ID is required")
        sys.exit(1)
    if not PLEX_URL:
        logger.error("Plex server URL is required")
        sys.exit(1)
    if not PLEX_TOKEN:
        logger.error("Plex authentication token is required")
        sys.exit(1)

    # Load processed movies
    processed_movies = load_processed_movies()

    # Start the bot
    try:
        logger.info(f"Starting Plex Discord Bot with check interval: {CHECK_INTERVAL} seconds")
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
