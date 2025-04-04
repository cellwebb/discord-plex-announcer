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
        movie_channel_id: int,
        new_shows_channel_id: int,
        recent_episodes_channel_id: int,
        bot_debug_channel_id: int = None,
        movie_library: str = "Movies",
        tv_library: str = "TV Shows",
        notify_movies: bool = True,
        notify_new_shows: bool = True,
        notify_recent_episodes: bool = True,
        recent_episode_days: int = 30,
        webhook_enabled: bool = False,
        webhook_port: int = 10000,
        webhook_host: str = "0.0.0.0",
    ):
        """Initialize the Discord bot."""
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
        self.webhook_enabled = webhook_enabled
        self.webhook_port = webhook_port
        self.webhook_host = webhook_host
        self.webhook_server = None

        # Internal state
        self.last_connected = False
        self.bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())
        self.start_time = time.time()

        # Set up Discord bot
        intents = discord.Intents.default()
        intents.message_content = True

        # Register commands and events
        self._setup_bot()

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
                startup_embed.set_footer(text="Plex Announcer Bot")

                try:
                    await debug_channel.send(embed=startup_embed)
                    logger.info("Sent startup message to bot debug channel")
                except Exception as e:
                    logger.error(f"Error sending startup message: {e}")

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

        self.bot.add_listener(on_ready)

    async def run(self):
        """Run the Discord bot."""
        # Start webhook server first if enabled
        webhook_server_started = False
        if self.webhook_enabled:
            try:
                from plex_announcer.core.webhook_server import PlexWebhookServer

                logger.info(f"Starting webhook server on {self.webhook_host}:{self.webhook_port}")
                self.webhook_server = PlexWebhookServer(
                    self, host=self.webhook_host, port=self.webhook_port
                )
                await self.webhook_server.start()
                webhook_server_started = True
                logger.info(
                    f"Webhook server started successfully on {self.webhook_host}:{self.webhook_port}"
                )
            except Exception as e:
                logger.error(f"Failed to start webhook server: {e}", exc_info=True)

        # Run the Discord bot
        try:
            logger.info("Starting Discord bot")
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}", exc_info=True)
        finally:
            if webhook_server_started and self.webhook_server:
                logger.info("Stopping webhook server")
                await self.webhook_server.stop()

    # Webhook handling methods
    async def announce_new_movie_from_webhook(self, metadata: dict):
        """Announce a new movie from webhook data."""
        if not self.notify_movies or not self.bot.is_ready():
            return

        logger.info(f"Processing webhook for new movie: {metadata.get('title')}")

        try:
            channel = self.bot.get_channel(self.movie_channel_id)
            if not channel:
                logger.error(f"Could not find movie channel with ID {self.movie_channel_id}")
                return

            # Basic movie info from webhook
            movie_data = {
                "title": metadata.get("title", "Unknown Title"),
                "summary": metadata.get("summary", "No summary available"),
                "year": metadata.get("year", "Unknown Year"),
                "tagline": metadata.get("tagline", ""),
                "thumb": metadata.get("thumb", ""),
                "art": metadata.get("art", ""),
                "duration": metadata.get("duration", 0),
                "rating": metadata.get("rating", 0.0),
                "added_at": int(time.time()),
            }

            # Create and send embed
            embed = EmbedBuilder.build_movie_embed(movie_data)
            await channel.send(embed=embed)
            logger.info(f"Announced new movie from webhook: {movie_data['title']}")
        except Exception as e:
            logger.error(f"Error announcing movie from webhook: {e}", exc_info=True)

    async def announce_new_episode_from_webhook(self, metadata: dict):
        """Announce a new episode from webhook data."""
        if not self.notify_recent_episodes or not self.bot.is_ready():
            return

        logger.info(f"Processing webhook for new episode: {metadata.get('title')}")

        try:
            channel = self.bot.get_channel(self.recent_episodes_channel_id)
            if not channel:
                logger.error(
                    f"Could not find episodes channel with ID {self.recent_episodes_channel_id}"
                )
                return

            # Basic episode info from webhook
            show_title = metadata.get("grandparentTitle", "Unknown Show")
            episode_data = {
                "title": metadata.get("title", "Unknown Title"),
                "summary": metadata.get("summary", "No summary available"),
                "season": metadata.get("parentIndex", 0),
                "episode": metadata.get("index", 0),
                "show_title": show_title,
                "thumb": metadata.get("thumb", ""),
                "art": metadata.get("art", ""),
                "grandparentThumb": metadata.get("grandparentThumb", ""),
                "duration": metadata.get("duration", 0),
                "added_at": int(time.time()),
            }

            # Create and send embed
            embed = EmbedBuilder.build_episode_embed(episode_data)
            await channel.send(embed=embed)
            logger.info(
                f"Announced new episode from webhook: {show_title} S{episode_data['season']}E{episode_data['episode']}"
            )
        except Exception as e:
            logger.error(f"Error announcing episode from webhook: {e}", exc_info=True)

    async def announce_new_show_from_webhook(self, metadata: dict):
        """Announce a new show from webhook data."""
        if not self.notify_new_shows or not self.bot.is_ready():
            return

        logger.info(f"Processing webhook for new show: {metadata.get('title')}")

        try:
            channel = self.bot.get_channel(self.new_shows_channel_id)
            if not channel:
                logger.error(
                    f"Could not find new shows channel with ID {self.new_shows_channel_id}"
                )
                return

            # Basic show info from webhook
            show_data = {
                "title": metadata.get("title", "Unknown Title"),
                "summary": metadata.get("summary", "No summary available"),
                "year": metadata.get("year", "Unknown Year"),
                "thumb": metadata.get("thumb", ""),
                "art": metadata.get("art", ""),
                "added_at": int(time.time()),
            }

            # Create and send embed
            embed = EmbedBuilder.build_show_embed(show_data)
            await channel.send(embed=embed)
            logger.info(f"Announced new show from webhook: {show_data['title']}")
        except Exception as e:
            logger.error(f"Error announcing show from webhook: {e}", exc_info=True)


# For backward compatibility
DiscordBot = PlexDiscordBot
