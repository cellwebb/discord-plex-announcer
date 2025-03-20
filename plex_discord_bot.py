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
from typing import Any, Dict, List, Optional, Set, cast

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from plexapi.exceptions import NotFound, Unauthorized
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie, Show

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
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "300"))
MOVIE_LIBRARY: str = os.getenv("MOVIE_LIBRARY", "Movies")
TV_LIBRARY: str = os.getenv("TV_LIBRARY", "TV Shows")
NOTIFY_MOVIES: bool = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
NOTIFY_TV: bool = os.getenv("NOTIFY_TV", "true").lower() == "true"
DATA_FILE: str = os.getenv("DATA_FILE", "processed_media.json")
TV_SHOW_BUFFER_FILE: str = os.getenv("TV_SHOW_BUFFER_FILE", "tv_show_buffer.json")
TV_BUFFER_TIME: int = int(os.getenv("TV_BUFFER_TIME", "7200"))  # 2 hours by default
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
                return False  # No point in retrying auth failures
            except (ConnectionError, TimeoutError) as e:
                retry_count += 1
                wait_time = 2**retry_count  # Exponential backoff
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
            recent_movies: List[Movie] = cast(
                List[Movie], library.search(libtype="movie", sort="addedAt:desc")
            )

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
            recent_episodes: List[Episode] = cast(
                List[Episode], library.searchEpisodes(sort="addedAt:desc")
            )

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

                    air_date: Optional[datetime] = None
                    if hasattr(episode, "originallyAvailableAt") and episode.originallyAvailableAt:
                        air_date = episode.originallyAvailableAt

                    new_episodes.append(
                        {
                            "type": "episode",
                            "key": episode.key,
                            "title": episode.title,
                            "show_title": episode.grandparentTitle,
                            "season_number": episode.parentIndex,
                            "episode_number": episode.index,
                            "year": episode.year,
                            "air_date": air_date,
                            "added_at": episode.addedAt.isoformat(),
                            "summary": episode.summary,
                            "content_rating": getattr(episode, "contentRating", "Not Rated"),
                            "rating": getattr(episode, "audienceRating", None),
                            "poster_url": poster_url,
                            "show_poster_url": show_poster_url,
                            "duration": episode.duration,
                            "directors": [
                                director.tag for director in getattr(episode, "directors", [])
                            ],
                            "writers": [writer.tag for writer in getattr(episode, "writers", [])],
                            "actors": [actor.tag for actor in getattr(episode, "roles", [])][:3],
                        }
                    )
                else:
                    break

            return new_episodes
        except Exception as e:
            logger.error(f"Error getting recently added episodes: {e}")
            return []

    def is_first_episode_of_show(self, show_title: str, processed_media: Set[str]) -> bool:
        """Determine if this is the first episode of a show that has been processed."""
        if not self.plex:
            if not self.connect():
                return False

        try:
            shows: List[Show] = cast(
                List[Show], self.plex.library.search(title=show_title, libtype="show")
            )
            if not shows:
                return False

            show: Show = shows[0]
            episodes: List[Episode] = show.episodes()

            for episode in episodes:
                if episode.key in processed_media:
                    return False

            return True
        except Exception as e:
            logger.error(f"Error checking if first episode of show: {e}")
            return False


def load_tv_buffer() -> Dict[str, Dict[str, Any]]:
    """Load TV show buffer from disk."""
    buffer_file = TV_SHOW_BUFFER_FILE
    try:
        if os.path.exists(buffer_file):
            with open(buffer_file, "r") as f:
                tv_buffer_data: Dict[str, Dict[str, Any]] = json.load(f)
                for show_title, data in tv_buffer_data.items():
                    if isinstance(data.get("last_updated"), str):
                        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
                return tv_buffer_data
        return {}
    except Exception as e:
        logger.error(f"Error loading TV show buffer: {e}")
        return {}


def save_tv_buffer(buffer: Dict[str, Dict[str, Any]]) -> bool:
    """Save TV show buffer to disk."""
    buffer_file = TV_SHOW_BUFFER_FILE
    # Prepare buffer for JSON serialization (convert datetime to string)
    buffer_to_save: Dict[str, Dict[str, Any]] = {}
    for show_title, data in buffer.items():
        buffer_copy = data.copy()
        if isinstance(buffer_copy.get("last_updated"), datetime):
            buffer_copy["last_updated"] = buffer_copy["last_updated"].isoformat()
        buffer_to_save[show_title] = buffer_copy

    try:
        with open(buffer_file, "w") as f:
            json.dump(buffer_to_save, f)
        return True
    except Exception as e:
        logger.error(f"Error saving TV show buffer: {e}")
        return False


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
async def on_ready() -> None:
    """Handler called when the Discord bot is ready and connected."""
    logger.info(f"Bot logged in as {bot.user}")
    check_for_new_media.start()


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

    # Buffer for TV shows to allow grouping across multiple episodes
    tv_buffer_time: int = (
        TV_BUFFER_TIME  # Group episodes from same show within TV_BUFFER_TIME seconds
    )
    tv_buffer: Dict[str, Dict[str, Any]] = load_tv_buffer()

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
                title=f"🎬 New Movie Available: {movie['title']} ({movie['year']})",
                description=(
                    movie["summary"][:2048] if movie["summary"] else "No summary available."
                ),
                color=0x00FF00,
            )

            if movie["rating"]:
                embed.add_field(name="Rating", value=f"⭐ {movie['rating']:.1f}/10", inline=True)

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

            if movie["poster_url"]:
                embed.set_thumbnail(url=movie["poster_url"])

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

        shows_to_process: Set[str] = set()

        for episode in recent_episodes:
            episode_key: str = episode["key"]

            if episode_key in processed_movies:
                continue

            is_recent_episode: bool = False
            if episode["air_date"]:
                thirty_days_ago: datetime = datetime.now() - timedelta(days=30)
                if episode["air_date"] >= thirty_days_ago.date():
                    is_recent_episode = True

            is_first_show_episode: bool = plex_monitor.is_first_episode_of_show(
                episode["show_title"], processed_movies
            )

            if is_recent_episode:
                logger.info(
                    f"Episode {episode['show_title']} S{episode['season_number']:02d}E"
                    + f"{episode['episode_number']:02d} is a recent episode (aired within 30 days)"
                )
            if is_first_show_episode:
                logger.info(
                    f"Episode {episode['show_title']} S{episode['season_number']:02d}E"
                    + f"{episode['episode_number']:02d} is the first episode of this show on the server"  # noqa: E501
                )

            if is_recent_episode or is_first_show_episode:
                show_title: str = episode["show_title"]
                shows_to_process.add(show_title)

                # If we already have a buffer for this show, add this episode to it
                if show_title in tv_buffer:
                    buffer_data: Dict[str, Any] = tv_buffer[show_title]
                    buffer_data["episodes"].append(episode)
                    buffer_data["last_updated"] = datetime.now()
                else:
                    # Create a new buffer for this show
                    tv_buffer[show_title] = {
                        "show_title": show_title,
                        "show_poster_url": episode["show_poster_url"],
                        "episodes": [episode],
                        "last_updated": datetime.now(),
                        "is_first_show": is_first_show_episode,
                    }

            # Mark as processed regardless
            processed_movies.add(episode_key)

        # Save the TV show buffer
        save_tv_buffer(tv_buffer)

        # Check for shows that haven't been updated in a while and should be sent
        current_time: datetime = datetime.now()
        shows_to_send: List[str] = []

        for show_title, data in list(tv_buffer.items()):
            time_since_update: float = (current_time - data["last_updated"]).total_seconds()

            # Send notification if:
            # 1. Buffer time has passed since last update, or
            # 2. We processed an episode for this show in this run and buffer time passed since first episode  # noqa: E501
            if (time_since_update >= tv_buffer_time) or (show_title in shows_to_process):
                shows_to_send.append(show_title)

        # Send notifications for shows that are ready
        for show_title in shows_to_send:
            show_data: Dict[str, Any] = tv_buffer[show_title]
            episodes: List[Dict[str, Any]] = show_data["episodes"]

            if not episodes:
                continue

            logger.info(f"Sending notification for {len(episodes)} episode(s) of {show_title}")

            embed_title: str = f"📺 New Episodes Available: {show_title}"
            embed_color: int = 0x3498DB

            if show_data.get("is_first_show", False):
                embed_title = f"📺 NEW SHOW: {show_title}"
                embed_color = 0x9B59B6

            embed: discord.Embed = discord.Embed(
                title=embed_title,
                description=f"{len(episodes)} new episode(s) added to Plex.",
                color=embed_color,
            )

            episode_list: str = ""
            for episode in episodes:
                episode_entry: str = (
                    f"• S{episode['season_number']:02d}E{episode['episode_number']:02d} - {episode['title']}"  # noqa: E501
                )

                if episode["air_date"]:
                    thirty_days_ago: datetime = datetime.now() - timedelta(days=30)
                    if episode["air_date"] >= thirty_days_ago.date():
                        episode_entry += " 📡 *Recently Aired*"

                episode_list += episode_entry + "\n"

            embed.add_field(name="Episodes", value=episode_list, inline=False)

            if len(episodes) == 1:
                episode: Dict[str, Any] = episodes[0]
                if episode["summary"]:
                    embed.description = episode["summary"][:2048]

                if episode["rating"]:
                    embed.add_field(
                        name="Rating",
                        value=f"⭐ {episode['rating']:.1f}/10",
                        inline=True,
                    )

                embed.add_field(name="Content Rating", value=episode["content_rating"], inline=True)
                embed.add_field(
                    name="Duration",
                    value=format_duration(episode["duration"]),
                    inline=True,
                )

                if episode.get("directors"):
                    embed.add_field(
                        name="Director(s)",
                        value=", ".join(episode["directors"]),
                        inline=True,
                    )

                if episode.get("writers"):
                    embed.add_field(
                        name="Writer(s)",
                        value=", ".join(episode["writers"]),
                        inline=True,
                    )

                if episode["actors"]:
                    embed.add_field(
                        name="Starring", value=", ".join(episode["actors"]), inline=True
                    )

                if episode["poster_url"]:
                    embed.set_image(url=episode["poster_url"])

            if show_data["show_poster_url"]:
                embed.set_thumbnail(url=show_data["show_poster_url"])

            embed.timestamp = datetime.now()
            embed.set_footer(text="Added to Plex")

            try:
                await channel.send(embed=embed)
                logger.info(
                    f"Sent notification for show: {show_title} with {len(episodes)} episode(s)"
                )

                # Remove from buffer after sending
                del tv_buffer[show_title]

                time.sleep(1)
            except Exception as e:
                logger.error(f"Error sending episode notification: {e}")

        # Save the TV show buffer again after processing
        save_tv_buffer(tv_buffer)

        save_processed_movies(processed_movies)


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

    # Add last check timestamp
    uptime = time.time() - START_TIME
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    embed.add_field(
        name="Uptime",
        value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s",
        inline=True,
    )

    embed.timestamp = datetime.now()
    await ctx.send(embed=embed)


@bot.command(name="healthcheck")
async def healthcheck(ctx: commands.Context) -> None:
    """Health check command to verify bot is running properly."""
    # Check Plex connectivity
    plex_monitor = PlexMonitor(PLEX_URL, PLEX_TOKEN)
    plex_status = "✅ Connected" if plex_monitor.connect() else "❌ Disconnected"

    # Check Discord channel connectivity
    channel = bot.get_channel(CHANNEL_ID)
    channel_status = "✅ Connected" if channel else "❌ Disconnected"

    embed = discord.Embed(
        title="Health Check",
        description="System health status",
        color=(
            0x00FF00
            if plex_status.startswith("✅") and channel_status.startswith("✅")
            else 0xFF0000
        ),
    )

    embed.add_field(name="Plex Server", value=plex_status, inline=True)
    embed.add_field(name="Discord Channel", value=channel_status, inline=True)
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
    await ctx.send(embed=embed)


def signal_handler(sig, frame):
    """Handle termination signals for clean shutdown."""
    logger.info("Received shutdown signal, saving data and exiting...")
    save_processed_movies(processed_movies)
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main() -> None:
    """
    Main function to run the bot.

    Handles command-line argument parsing, configuration validation,
    and starting the Discord bot.
    """
    global processed_movies, DISCORD_TOKEN, CHANNEL_ID, PLEX_URL, PLEX_TOKEN, CHECK_INTERVAL
    global MOVIE_LIBRARY, TV_LIBRARY, NOTIFY_MOVIES, NOTIFY_TV, DATA_FILE

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Plex Discord Bot - Notifications for new movies and TV episodes"
    )
    parser.add_argument("--token", help="Discord bot token")
    parser.add_argument("--channel", type=int, help="Discord channel ID")
    parser.add_argument("--plex-url", help="Plex server URL")
    parser.add_argument("--plex-token", help="Plex server token")
    parser.add_argument("--interval", type=int, help="Check interval in seconds")
    parser.add_argument("--movie-library", help="Plex movie library name")
    parser.add_argument("--tv-library", help="Plex TV show library name")
    parser.add_argument(
        "--notify-movies",
        choices=["true", "false"],
        help="Enable/disable movie notifications",
    )
    parser.add_argument(
        "--notify-tv",
        choices=["true", "false"],
        help="Enable/disable TV show notifications",
    )
    parser.add_argument("--data-file", help="File to store processed media")

    args: argparse.Namespace = parser.parse_args()

    # Override environment variables with command line arguments if provided
    if args.token:
        DISCORD_TOKEN = args.token
    if args.channel:
        CHANNEL_ID = args.channel
    if args.plex_url:
        PLEX_URL = args.plex_url
    if args.plex_token:
        PLEX_TOKEN = args.plex_token
    if args.interval:
        CHECK_INTERVAL = args.interval
    if args.movie_library:
        MOVIE_LIBRARY = args.movie_library
    if args.tv_library:
        TV_LIBRARY = args.tv_library
    if args.notify_movies:
        NOTIFY_MOVIES = args.notify_movies.lower() == "true"
    if args.notify_tv:
        NOTIFY_TV = args.notify_tv.lower() == "true"
    if args.data_file:
        DATA_FILE = args.data_file

    # Validate required settings
    if not DISCORD_TOKEN:
        logger.error(
            "Discord token is required. Set DISCORD_TOKEN environment variable or use --token"
        )
        return

    if CHANNEL_ID == 0:
        logger.error(
            "Discord channel ID is required. Set CHANNEL_ID environment variable or use --channel"
        )
        return

    if not PLEX_TOKEN:
        logger.error(
            "Plex token is required. Set PLEX_TOKEN environment variable or use --plex-token"
        )
        return

    if not NOTIFY_MOVIES and not NOTIFY_TV:
        logger.error("Both movie and TV notifications are disabled. Enable at least one.")
        return

    processed_movies = load_processed_movies()
    logger.info(f"Loaded {len(processed_movies)} processed media items from {DATA_FILE}")

    logger.info(f"Monitoring Plex server at {PLEX_URL}")
    if NOTIFY_MOVIES:
        logger.info(f"Movie notifications enabled for library: {MOVIE_LIBRARY}")
    else:
        logger.info("Movie notifications disabled")

    if NOTIFY_TV:
        logger.info(f"TV show notifications enabled for library: {TV_LIBRARY}")
    else:
        logger.info("TV show notifications disabled")

    logger.info("Starting bot...")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()
