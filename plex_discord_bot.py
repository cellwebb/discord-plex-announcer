import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union

import discord
import requests
from discord.ext import commands, tasks
from dotenv import load_dotenv
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("plex_discord_bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger("plex_discord_bot")

# Load environment variables from .env file
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))  # Default to 5 minutes
MOVIE_LIBRARY = os.getenv("MOVIE_LIBRARY", "Movies")
TV_LIBRARY = os.getenv("TV_LIBRARY", "TV Shows")
NOTIFY_MOVIES = os.getenv("NOTIFY_MOVIES", "true").lower() == "true"
NOTIFY_TV = os.getenv("NOTIFY_TV", "true").lower() == "true"
DATA_FILE = os.getenv("DATA_FILE", "processed_media.json")

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global state
processed_movies: Set[str] = set()


class PlexMonitor:
    def __init__(self, plex_url: str, plex_token: str):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.plex = None
        self.connect()

    def connect(self) -> bool:
        """Connect to the Plex server"""
        try:
            self.plex = PlexServer(self.plex_url, self.plex_token)
            logger.info(f"Connected to Plex server at {self.plex_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Plex: {e}")
            return False

    def get_library(self, library_name: str):
        """Get a specific library section"""
        if not self.plex:
            if not self.connect():
                return None

        try:
            library = self.plex.library.section(library_name)
            logger.info(f"Found library: {library_name}")
            return library
        except Exception as e:
            logger.error(f"Failed to find library '{library_name}': {e}")
            return None

    def get_recently_added_movies(self, library_name: str, days: int = 1) -> List[Dict]:
        """Get recently added movies from the Plex library"""
        if not self.plex:
            if not self.connect():
                return []

        try:
            library = self.get_library(library_name)
            if not library:
                return []

            # Get movies added in the last 'days' days
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_movies = library.search(libtype="movie", sort="addedAt:desc")

            # Filter movies that were added after the cutoff date
            new_movies = []
            for movie in recent_movies:
                if movie.addedAt > cutoff_date:
                    # Convert to dictionary for easier processing
                    poster_url = None
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
                            "content_rating": getattr(
                                movie, "contentRating", "Not Rated"
                            ),
                            "rating": getattr(movie, "rating", None),
                            "poster_url": poster_url,
                            "duration": movie.duration,
                            "genres": [
                                genre.tag for genre in getattr(movie, "genres", [])
                            ],
                            "directors": [
                                director.tag
                                for director in getattr(movie, "directors", [])
                            ],
                            "actors": [
                                actor.tag for actor in getattr(movie, "roles", [])
                            ][
                                :3
                            ],  # Limit to top 3 actors
                        }
                    )
                else:
                    # Since we're sorting by addedAt descending, we can break once we hit older movies
                    break

            return new_movies
        except Exception as e:
            logger.error(f"Error getting recently added movies: {e}")
            return []

    def get_recently_added_episodes(
        self, library_name: str, days: int = 1
    ) -> List[Dict]:
        """Get recently added TV episodes from the Plex library"""
        if not self.plex:
            if not self.connect():
                return []

        try:
            library = self.get_library(library_name)
            if not library:
                return []

            # Get episodes added in the last 'days' days
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_episodes = library.searchEpisodes(sort="addedAt:desc")

            # Filter episodes that were added after the cutoff date
            new_episodes = []
            for episode in recent_episodes:
                if episode.addedAt > cutoff_date:
                    # Convert to dictionary for easier processing
                    poster_url = None
                    if episode.thumb:
                        poster_url = f"{self.plex_url}{episode.thumb}?X-Plex-Token={self.plex_token}"

                    show_poster_url = None
                    if episode.grandparentThumb:
                        show_poster_url = f"{self.plex_url}{episode.grandparentThumb}?X-Plex-Token={self.plex_token}"

                    # Episode data
                    new_episodes.append(
                        {
                            "type": "episode",
                            "key": episode.key,
                            "title": episode.title,
                            "show_title": episode.grandparentTitle,
                            "season_number": episode.parentIndex,
                            "episode_number": episode.index,
                            "year": episode.year,
                            "added_at": episode.addedAt.isoformat(),
                            "summary": episode.summary,
                            "content_rating": getattr(
                                episode, "contentRating", "Not Rated"
                            ),
                            "rating": getattr(episode, "audienceRating", None),
                            "poster_url": poster_url,
                            "show_poster_url": show_poster_url,
                            "duration": episode.duration,
                            "directors": [
                                director.tag
                                for director in getattr(episode, "directors", [])
                            ],
                            "writers": [
                                writer.tag for writer in getattr(episode, "writers", [])
                            ],
                            "actors": [
                                actor.tag for actor in getattr(episode, "roles", [])
                            ][
                                :3
                            ],  # Limit to top 3 actors
                        }
                    )
                else:
                    # Since we're sorting by addedAt descending, we can break once we hit older episodes
                    break

            return new_episodes
        except Exception as e:
            logger.error(f"Error getting recently added episodes: {e}")
            return []


def load_processed_movies() -> Set[str]:
    """Load the list of already processed media items from file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Error loading processed media: {e}")
        return set()


def save_processed_movies(movies: Set[str]) -> None:
    """Save the list of processed media items to file"""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(list(movies), f)
    except Exception as e:
        logger.error(f"Error saving processed media: {e}")


def format_duration(milliseconds: int) -> str:
    """Format milliseconds to HH:MM format"""
    total_seconds = milliseconds // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"


@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f"Bot logged in as {bot.user}")
    check_for_new_media.start()


@tasks.loop(seconds=CHECK_INTERVAL)
async def check_for_new_media():
    """Check for new movies and TV episodes and send notifications"""
    global processed_movies

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find channel with ID {CHANNEL_ID}")
        return

    logger.info("Checking for new media...")

    # Initialize the Plex monitor
    plex_monitor = PlexMonitor(PLEX_URL, PLEX_TOKEN)

    # Check for new movies if enabled
    if NOTIFY_MOVIES:
        logger.info(f"Checking for new movies in library: {MOVIE_LIBRARY}")
        recent_movies = plex_monitor.get_recently_added_movies(MOVIE_LIBRARY, days=1)

        for movie in recent_movies:
            movie_key = movie["key"]

            # Skip if we've already processed this movie
            if movie_key in processed_movies:
                continue

            logger.info(f"Found new movie: {movie['title']} ({movie['year']})")

            # Create a nice embed for Discord
            embed = discord.Embed(
                title=f"🎬 New Movie Available: {movie['title']} ({movie['year']})",
                description=(
                    movie["summary"][:2048]
                    if movie["summary"]
                    else "No summary available."
                ),
                color=0x00FF00,
            )

            # Add movie details
            if movie["rating"]:
                embed.add_field(
                    name="Rating", value=f"⭐ {movie['rating']:.1f}/10", inline=True
                )

            embed.add_field(
                name="Content Rating", value=movie["content_rating"], inline=True
            )
            embed.add_field(
                name="Duration", value=format_duration(movie["duration"]), inline=True
            )

            if movie["genres"]:
                embed.add_field(
                    name="Genres", value=", ".join(movie["genres"]), inline=True
                )

            if movie["directors"]:
                embed.add_field(
                    name="Director(s)", value=", ".join(movie["directors"]), inline=True
                )

            if movie["actors"]:
                embed.add_field(
                    name="Starring", value=", ".join(movie["actors"]), inline=True
                )

            # Add the poster as thumbnail if available
            if movie["poster_url"]:
                embed.set_thumbnail(url=movie["poster_url"])

            # Add timestamp
            embed.timestamp = datetime.now()
            embed.set_footer(text="Added to Plex")

            # Send the message
            try:
                await channel.send(embed=embed)
                logger.info(f"Sent notification for movie: {movie['title']}")

                # Add to processed movies
                processed_movies.add(movie_key)
                save_processed_movies(processed_movies)

                # Sleep briefly to avoid rate limiting
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error sending movie notification: {e}")

    # Check for new TV episodes if enabled
    if NOTIFY_TV:
        logger.info(f"Checking for new TV episodes in library: {TV_LIBRARY}")
        recent_episodes = plex_monitor.get_recently_added_episodes(TV_LIBRARY, days=1)

        for episode in recent_episodes:
            episode_key = episode["key"]

            # Skip if we've already processed this episode
            if episode_key in processed_movies:
                continue

            logger.info(
                f"Found new episode: {episode['show_title']} - S{episode['season_number']:02d}E{episode['episode_number']:02d} - {episode['title']}"
            )

            # Create a nice embed for Discord
            embed = discord.Embed(
                title=f"📺 New Episode Available: {episode['show_title']}",
                description=f"**S{episode['season_number']:02d}E{episode['episode_number']:02d} - {episode['title']}**\n\n{episode['summary'][:2048] if episode['summary'] else 'No summary available.'}",
                color=0x3498DB,  # Blue color for TV shows
            )

            # Add episode details
            if episode["rating"]:
                embed.add_field(
                    name="Rating", value=f"⭐ {episode['rating']:.1f}/10", inline=True
                )

            embed.add_field(
                name="Content Rating", value=episode["content_rating"], inline=True
            )
            embed.add_field(
                name="Duration", value=format_duration(episode["duration"]), inline=True
            )

            if episode["directors"]:
                embed.add_field(
                    name="Director(s)",
                    value=", ".join(episode["directors"]),
                    inline=True,
                )

            if episode.get("writers"):
                embed.add_field(
                    name="Writer(s)", value=", ".join(episode["writers"]), inline=True
                )

            if episode["actors"]:
                embed.add_field(
                    name="Starring", value=", ".join(episode["actors"]), inline=True
                )

            # Add the episode thumbnail if available
            if episode["poster_url"]:
                embed.set_image(url=episode["poster_url"])

            # Add the show poster as thumbnail if available
            if episode["show_poster_url"]:
                embed.set_thumbnail(url=episode["show_poster_url"])

            # Add timestamp
            embed.timestamp = datetime.now()
            embed.set_footer(text="Added to Plex")

            # Send the message
            try:
                await channel.send(embed=embed)
                logger.info(
                    f"Sent notification for episode: {episode['show_title']} S{episode['season_number']:02d}E{episode['episode_number']:02d}"
                )

                # Add to processed movies
                processed_movies.add(episode_key)
                save_processed_movies(processed_movies)

                # Sleep briefly to avoid rate limiting
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error sending episode notification: {e}")


@bot.command(name="checkplex")
async def check_plex(ctx):
    """Manual command to check for new media"""
    await ctx.send("Checking for new movies and TV episodes...")
    await check_for_new_media()
    await ctx.send("Check complete!")


@bot.command(name="status")
async def status(ctx):
    """Show bot status"""
    global processed_movies

    embed = discord.Embed(
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

    embed.add_field(
        name="Check Interval", value=f"{CHECK_INTERVAL} seconds", inline=True
    )
    embed.add_field(
        name="Processed Media", value=str(len(processed_movies)), inline=True
    )

    embed.timestamp = datetime.now()
    await ctx.send(embed=embed)


def main():
    """Main function to run the bot"""
    global processed_movies, DISCORD_TOKEN, CHANNEL_ID, PLEX_URL, PLEX_TOKEN, CHECK_INTERVAL
    global MOVIE_LIBRARY, TV_LIBRARY, NOTIFY_MOVIES, NOTIFY_TV, DATA_FILE

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Plex Discord Bot - Send notifications for new movies and TV episodes"
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

    args = parser.parse_args()

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
        logger.error(
            "Both movie and TV notifications are disabled. Enable at least one."
        )
        return

    # Load processed media from file
    processed_movies = load_processed_movies()
    logger.info(
        f"Loaded {len(processed_movies)} processed media items from {DATA_FILE}"
    )

    # Log configuration
    logger.info(f"Monitoring Plex server at {PLEX_URL}")
    if NOTIFY_MOVIES:
        logger.info(f"Movie notifications enabled for library: {MOVIE_LIBRARY}")
    else:
        logger.info("Movie notifications disabled")

    if NOTIFY_TV:
        logger.info(f"TV show notifications enabled for library: {TV_LIBRARY}")
    else:
        logger.info("TV show notifications disabled")

    # Start the bot
    logger.info("Starting bot...")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()
