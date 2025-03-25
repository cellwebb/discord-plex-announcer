"""
Discord bot implementation for sending Plex media notifications.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands, tasks

from plex_announcer.utils.embed_builder import EmbedBuilder
from plex_announcer.utils.media_storage import load_last_check_time, save_last_check_time

logger = logging.getLogger("plex_discord_bot")


class PlexDiscordBot:
    """Discord bot for announcing new Plex media."""

    def __init__(
        self,
        token: str,
        plex_monitor,
        check_interval: int,
        movie_channel_id: int,
        new_shows_channel_id: int,
        recent_episodes_channel_id: int,
        bot_debug_channel_id: int,
        notify_movies: bool = True,
        notify_new_shows: bool = True,
        notify_recent_episodes: bool = True,
        recent_episode_days: int = 30,
        movie_library: str = "Movies",
        tv_library: str = "TV Shows",
    ):
        """Initialize the Discord bot with configuration parameters."""
        self.token = token
        self.movie_channel_id = movie_channel_id  # Channel for movie announcements
        self.new_shows_channel_id = new_shows_channel_id  # Channel for new show announcements
        self.recent_episodes_channel_id = (
            recent_episodes_channel_id  # Channel for recent episode announcements
        )
        self.bot_debug_channel_id = bot_debug_channel_id  # Channel to show bot presence in
        self.plex_monitor = plex_monitor
        self.movie_library = movie_library
        self.tv_library = tv_library
        self.notify_movies = notify_movies
        self.notify_new_shows = notify_new_shows
        self.notify_recent_episodes = notify_recent_episodes
        self.recent_episode_days = recent_episode_days
        self.check_interval = check_interval
        self.processed_media = set()
        self.start_time = time.time()

        self.last_check_time: Optional[datetime] = None

        # Set up Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        # Register commands and events
        self._setup_bot()

        # Load last check time
        self.last_check_time = load_last_check_time(self.timestamp_file)
        if self.last_check_time:
            logger.info(f"Loaded last check time: {self.last_check_time.isoformat()}")
        else:
            logger.info("No previous check time found, will check all recent media")

    @property
    def timestamp_file(self) -> str:
        """Get the path to the timestamp file."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "last_check_time.txt")

    @property
    def startup_flag_file(self) -> str:
        """Get the path to the startup flag file."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "startup_completed.txt")

    def _setup_bot(self):
        """Set up bot commands and event handlers."""

        @self.bot.event
        async def on_ready():
            """Handle the bot ready event."""
            logger.info(f"Logged in as {self.bot.user.name} ({self.bot.user.id})")
            logger.info(f"Connected to {len(self.bot.guilds)} guilds")

            # Debug: List all guilds and channels
            for guild in self.bot.guilds:
                logger.info(f"Guild: {guild.name} (ID: {guild.id})")
                logger.info(f"Channels in {guild.name}:")
                for channel in guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        logger.info(f"  - #{channel.name} (ID: {channel.id})")

            # Set bot presence based on recent media
            debug_channel = self.bot.get_channel(self.bot_debug_channel_id)

            # Try to get recent movies
            try:
                # Check if Plex is connected
                if not self.plex_monitor.plex:
                    logger.warning("Plex server not connected, using default activity")
                    activity_name = "for Plex to connect..."
                else:
                    recent_movies = self.plex_monitor.get_recently_added_movies(days=7)
                    recent_episodes = self.plex_monitor.get_recently_added_episodes(days=7)

                    if recent_movies and len(recent_movies) > 0:
                        # Use the most recent movie for presence
                        latest_movie = recent_movies[0]
                        movie_title = latest_movie.get("title", "a movie")
                        activity_name = f"📽️ {movie_title}"
                        logger.info(f"Setting activity to recent movie: {movie_title}")
                    elif recent_episodes and len(recent_episodes) > 0:
                        # Use the most recent show for presence
                        latest_episode = recent_episodes[0]
                        show_title = latest_episode.get("show_title", "a show")
                        activity_name = f"📺 {show_title}"
                        logger.info(f"Setting activity to recent show: {show_title}")
                    else:
                        # Default presence when no recent media
                        activity_name = "for new movies..."
                        logger.info("No recent media found, setting default activity")
            except Exception as e:
                logger.error(f"Error setting activity status: {e}")
                # Default presence on error
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching, name="Plex for new media"
                    )
                )
                return

            # Set the activity
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=activity_name)
            )

            if debug_channel:
                logger.info(f"Debug channel found: #{debug_channel.name}")
            else:
                logger.warning(f"Debug channel ID {self.bot_debug_channel_id} not found")
            # Check if startup has already been completed
            startup_completed = os.path.exists(self.startup_flag_file)

            # Only execute the startup sequence once
            if not startup_completed:
                logger.info("First-time startup detected, sending welcome message")

                # Create the startup flag file to prevent future startup messages
                try:
                    with open(self.startup_flag_file, "w") as f:
                        f.write(f"Startup completed at {datetime.now().isoformat()}")
                    logger.info(f"Created startup flag file at {self.startup_flag_file}")
                except Exception as e:
                    logger.error(f"Failed to create startup flag file: {e}")

                # Find default channel and send startup message
                debug_channel = self.bot.get_channel(self.bot_debug_channel_id)
                if debug_channel:
                    logger.info(f"Found bot debug channel: #{debug_channel.name}")

                    # Send startup message
                    startup_embed = discord.Embed(
                        title="Plex Announcer Bot Online",
                        description="The Plex Announcer Bot is now online and monitoring your Plex server for new content.",  # noqa: E501
                        color=discord.Color.green(),
                        timestamp=datetime.now(),
                    )
                    startup_embed.add_field(
                        name="Monitoring Libraries",
                        value=f"Movies: {self.movie_library}\nTV Shows: {self.tv_library}",
                        inline=False,
                    )
                    startup_embed.add_field(
                        name="Check Interval",
                        value=f"{self.check_interval // 60} minutes",
                        inline=True,
                    )
                    if self.last_check_time:
                        startup_embed.add_field(
                            name="Last Check Time",
                            value=self.last_check_time.strftime("%Y-%m-%d %H:%M:%S"),
                            inline=True,
                        )
                    startup_embed.set_footer(text="Plex Announcer Bot")

                    try:
                        await debug_channel.send(embed=startup_embed)
                        logger.info("Sent startup message to bot debug channel")
                    except Exception as e:
                        logger.error(f"Error sending startup message: {e}")

                    # Perform initial check for new media
                    logger.info("Performing initial check for new media...")
                    try:
                        await self._check_for_new_media(manual=False)
                    except Exception as e:
                        logger.error(f"Error during initial check: {e}", exc_info=True)
                        # Send error message to presence channel
                        error_embed = discord.Embed(
                            title="Plex Connection Error",
                            description="Failed to connect to Plex server during initial check. Will retry on next scheduled check.",
                            color=discord.Color.red(),
                            timestamp=datetime.now(),
                        )
                        error_embed.add_field(
                            name="Error",
                            value=str(e)[:1024],  # Limit to 1024 characters for Discord embed
                            inline=False,
                        )
                        error_embed.set_footer(text="Plex Announcer Bot")

                        try:
                            await debug_channel.send(embed=error_embed)
                            logger.info("Sent error message to bot debug channel")
                        except Exception as e_inner:
                            logger.error(f"Error sending error message: {e_inner}")
                else:
                    logger.error(
                        f"Could not find bot debug channel with ID {self.bot_debug_channel_id}"
                    )
            else:
                logger.info("Bot reconnected, skipping welcome message")

            # Check for specialized channels
            if self.movie_channel_id:
                movie_channel = self.bot.get_channel(self.movie_channel_id)
                if movie_channel:
                    logger.info(f"Found movie announcement channel: #{movie_channel.name}")
                else:
                    logger.error(f"Could not find movie channel with ID {self.movie_channel_id}")

            if self.new_shows_channel_id:
                new_shows_channel = self.bot.get_channel(self.new_shows_channel_id)
                if new_shows_channel:
                    logger.info(f"Found new shows announcement channel: #{new_shows_channel.name}")
                else:
                    logger.error(
                        f"Could not find new shows channel with ID {self.new_shows_channel_id}"
                    )

            if self.recent_episodes_channel_id:
                recent_episodes_channel = self.bot.get_channel(self.recent_episodes_channel_id)
                if recent_episodes_channel:
                    logger.info(
                        f"Found recent episodes announcement channel: #{recent_episodes_channel.name}"  # noqa: E501
                    )
                else:
                    logger.error(
                        f"Could not find recent episodes channel with ID {self.recent_episodes_channel_id}"  # noqa: E501
                    )

        @self.bot.command(name="check")
        async def check_plex(ctx: commands.Context):
            """Discord command to manually check for new media."""
            if not ctx.guild:
                await ctx.send("This command can only be used in a server.")
                return

            await ctx.send("Manually checking for new media...")
            await self._check_for_new_media(manual=True)
            await ctx.send("Check completed!")

        @self.bot.command(name="status")
        async def status(ctx: commands.Context):
            """Display the current bot status and configuration."""
            if not ctx.guild:
                await ctx.send("This command can only be used in a server.")
                return

            uptime = time.time() - self.start_time
            days, remainder = divmod(uptime, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

            embed = discord.Embed(
                title="Plex Discord Bot Status",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="Uptime", value=uptime_str, inline=False)
            embed.add_field(name="Movie Library", value=self.movie_library, inline=True)
            embed.add_field(name="TV Library", value=self.tv_library, inline=True)
            embed.add_field(
                name="Check Interval",
                value=f"{self.check_interval // 60} minutes",
                inline=True,
            )
            embed.add_field(
                name="Notify Movies",
                value="Yes" if self.notify_movies else "No",
                inline=True,
            )
            embed.add_field(
                name="Notify New Shows",
                value="Yes" if self.notify_new_shows else "No",
                inline=True,
            )
            embed.add_field(
                name="Notify Recent Episodes",
                value="Yes" if self.notify_recent_episodes else "No",
                inline=True,
            )
            embed.add_field(
                name="Recent Episode Days",
                value=str(self.recent_episode_days),
                inline=True,
            )

            if self.last_check_time:
                embed.add_field(
                    name="Last Check Time",
                    value=self.last_check_time.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True,
                )

            # Add channel information
            movie_channel = self.bot.get_channel(self.movie_channel_id)
            movie_channel_name = f"#{movie_channel.name}" if movie_channel else "Not found"
            embed.add_field(name="Movie Channel", value=movie_channel_name, inline=True)

            new_shows_channel = self.bot.get_channel(self.new_shows_channel_id)
            new_shows_channel_name = (
                f"#{new_shows_channel.name}" if new_shows_channel else "Not found"
            )
            embed.add_field(name="New Shows Channel", value=new_shows_channel_name, inline=True)

            recent_episodes_channel = self.bot.get_channel(self.recent_episodes_channel_id)
            recent_episodes_name = (
                f"#{recent_episodes_channel.name}" if recent_episodes_channel else "Not found"
            )
            embed.add_field(
                name="Recent Episodes Channel",
                value=recent_episodes_name,
                inline=True,
            )

            debug_channel = self.bot.get_channel(self.bot_debug_channel_id)
            debug_channel_name = f"#{debug_channel.name}" if debug_channel else "Not found"
            embed.add_field(name="Debug Channel", value=debug_channel_name, inline=True)

            embed.add_field(name="Media Entries", value=str(len(self.processed_media)), inline=True)

            await ctx.send(embed=embed)

        @self.bot.command(name="healthcheck")
        async def healthcheck(ctx: commands.Context):
            """Check if the bot can connect to Plex and Discord."""
            if not ctx.guild:
                await ctx.send("This command can only be used in a server.")
                return

            embed = discord.Embed(
                title="Plex Discord Bot Health Check",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            # Check Discord connection
            embed.add_field(name="Discord Connection", value="✅ Connected", inline=False)

            # Check Plex connection
            plex_connected = self.plex_monitor.connect()
            if plex_connected:
                embed.add_field(
                    name="Plex Connection",
                    value=f"✅ Connected to {self.plex_monitor.plex_base_url}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Plex Connection",
                    value="❌ Failed to connect to Plex server",
                    inline=False,
                )

            # Check libraries
            if plex_connected:
                movie_library = self.plex_monitor.get_library(self.movie_library)
                if movie_library:
                    embed.add_field(
                        name=f"{self.movie_library} Library",
                        value="✅ Available",
                        inline=True,
                    )
                else:
                    embed.add_field(
                        name=f"{self.movie_library} Library",
                        value="❌ Not found",
                        inline=True,
                    )

                tv_library = self.plex_monitor.get_library(self.tv_library)
                if tv_library:
                    embed.add_field(
                        name=f"{self.tv_library} Library",
                        value="✅ Available",
                        inline=True,
                    )
                else:
                    embed.add_field(
                        name=f"{self.tv_library} Library",
                        value="❌ Not found",
                        inline=True,
                    )

            await ctx.send(embed=embed)

        # Set up the task to check for new media
        @tasks.loop(seconds=self.check_interval)
        async def check_media_task():
            await self.bot.wait_until_ready()
            await self._check_for_new_media()

        self.bot.add_listener(on_ready)
        self.check_media_task = check_media_task

    async def run(self):
        """Run the Discord bot."""
        # Start the media check task
        self.check_media_task.start()

        try:
            # Run the bot with a timeout
            logger.info("Starting Discord bot connection")
            # Run the bot with a timeout
            await asyncio.wait_for(self.bot.start(self.token), timeout=60)
        except asyncio.TimeoutError:
            logger.error(
                "Timed out while connecting to Discord. Please check your connection and token."
            )
            return
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
            return

    async def _check_for_new_media(self, manual: bool = False):
        """Check for new media and send Discord notifications."""
        if not self.bot.is_ready():
            logger.warning("Bot not ready, skipping media check")
            return

        # Check if Plex is connected
        if not self.plex_monitor.plex:
            logger.warning("Plex server not connected, attempting to reconnect...")
            # Try to reconnect
            if not self.plex_monitor.connect():
                logger.error("Failed to connect to Plex server, skipping media check")

                # If this was a manual check, send a message to the user
                if manual and self.bot.is_ready():
                    debug_channel = self.bot.get_channel(self.bot_debug_channel_id)
                    if debug_channel:
                        error_embed = discord.Embed(
                            title="Plex Connection Error",
                            description="Failed to connect to Plex server. Will retry on next scheduled check.",
                            color=discord.Color.red(),
                            timestamp=datetime.now(),
                        )
                        await debug_channel.send(embed=error_embed)
                return
            else:
                logger.info("Successfully reconnected to Plex server")

        # Record the current time at the start of the check
        current_check_time = datetime.now()

        logger.info("Checking for new media...")
        if self.last_check_time:
            logger.info(f"Looking for content added since {self.last_check_time.isoformat()}")
        else:
            logger.info("No previous check time, checking all recent content")

        # Get the default notification channel
        movie_channel = self.bot.get_channel(self.movie_channel_id)
        if not movie_channel:
            logger.error(f"Could not find movie channel with ID {self.movie_channel_id}")
            return

        # Get specialized channels if configured
        new_shows_channel = self.bot.get_channel(self.new_shows_channel_id)
        recent_episodes_channel = self.bot.get_channel(self.recent_episodes_channel_id)

        new_items = []

        # Check for new movies
        if self.notify_movies:
            movies = self.plex_monitor.get_recently_added_movies(
                since_datetime=self.last_check_time, days=1
            )
            for movie in movies:
                if movie["key"] not in self.processed_media:
                    new_items.append({"item": movie, "channel": movie_channel})
                    self.processed_media.add(movie["key"])

        # Check for new TV episodes
        if self.notify_new_shows or self.notify_recent_episodes:
            episodes = self.plex_monitor.get_recently_added_episodes(
                since_datetime=self.last_check_time, days=1
            )

            for episode in episodes:
                if episode["key"] not in self.processed_media:
                    # Check if this is a new show (first episode of first season)
                    is_first_episode = (
                        episode["season_number"] == 1 and episode["episode_number"] == 1
                    )

                    # Check if the episode recently aired (if it has an air date)
                    recently_aired = False
                    if episode.get("air_date"):
                        try:
                            air_date = datetime.fromisoformat(episode["air_date"])
                            recently_aired = (
                                datetime.now() - air_date
                            ).days <= self.recent_episode_days
                        except (ValueError, TypeError):
                            recently_aired = False

                    # Only add episodes that match our notification criteria
                    should_add = False
                    target_channel = movie_channel

                    # Add if it's a new show and we're notifying for new shows
                    if self.notify_new_shows and is_first_episode:
                        should_add = True
                        target_channel = new_shows_channel

                    # Add if it recently aired and we're notifying for recent episodes
                    elif self.notify_recent_episodes and recently_aired:
                        should_add = True
                        target_channel = recent_episodes_channel

                    if should_add:
                        new_items.append({"item": episode, "channel": target_channel})

                    # Mark as processed regardless
                    self.processed_media.add(episode["key"])

        # Send notifications for new items
        for item_data in new_items:
            item = item_data["item"]
            channel = item_data["channel"]

            if isinstance(item, dict) and item.get("type") == "movie":
                embed = EmbedBuilder.create_movie_embed(item)
                await channel.send(embed=embed)
            elif isinstance(item, dict) and item.get("type") == "episode":
                embed = EmbedBuilder.create_episode_embed(item)
                await channel.send(embed=embed)

        # Update and save the last check time
        self.last_check_time = current_check_time
        save_last_check_time(self.last_check_time, self.timestamp_file)
        logger.info(f"Updated last check time to {self.last_check_time.isoformat()}")

        if new_items:
            logger.info(f"Sent notifications for {len(new_items)} new items")
        else:
            logger.info("No new media found")

        if manual:
            if new_items:
                logger.info(f"Found {len(new_items)} new items")
                return f"Found {len(new_items)} new items"
            else:
                logger.info("No new items found")
                return "No new items found"


# For backward compatibility
DiscordBot = PlexDiscordBot
