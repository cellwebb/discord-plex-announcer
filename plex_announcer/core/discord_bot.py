"""
Discord bot implementation for sending Plex media notifications.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Set, Any

import discord
from discord.ext import commands, tasks

from plex_announcer.utils.media_storage import load_processed_media, save_processed_media
from plex_announcer.utils.formatting import format_duration

logger = logging.getLogger("plex_discord_bot")


class PlexDiscordBot:
    """Discord bot for announcing new Plex media."""

    def __init__(
        self,
        token: str,
        channel_id: int,
        plex_monitor,
        check_interval: int,
        data_file: str,
        notify_movies: bool = True,
        notify_new_shows: bool = True,
        notify_recent_episodes: bool = True,
        recent_episode_days: int = 30,
        movie_library: str = "Movies",
        tv_library: str = "TV Shows",
    ):
        """Initialize the Discord bot with configuration parameters."""
        self.token = token
        self.channel_id = channel_id
        self.plex_monitor = plex_monitor
        self.movie_library = movie_library
        self.tv_library = tv_library
        self.notify_movies = notify_movies
        self.notify_new_shows = notify_new_shows
        self.notify_recent_episodes = notify_recent_episodes
        self.recent_episode_days = recent_episode_days
        self.check_interval = check_interval
        self.data_file = data_file
        self.processed_media: Set[str] = set()
        self.start_time: float = time.time()
        
        # Set up Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Register commands and events
        self._setup_bot()
        
        # Load processed media from storage
        self.processed_media = load_processed_media(self.data_file)

    def _setup_bot(self):
        """Set up bot commands and event handlers."""
        
        @self.bot.event
        async def on_ready():
            logger.info(f"Logged in as {self.bot.user.name} ({self.bot.user.id})")
            logger.info(f"Connected to {len(self.bot.guilds)} guilds")
            
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                logger.info(f"Found announcement channel: #{channel.name}")
                # Perform initial check for new media
                logger.info("Performing initial check for new media...")
                try:
                    await self._check_for_new_media(manual=True)
                    logger.info("Initial check completed successfully")
                except Exception as e:
                    logger.error(f"Error during initial check: {e}", exc_info=True)
            else:
                logger.error(f"Could not find channel with ID {self.channel_id}")
        
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
            embed.add_field(name="Check Interval", value=f"{self.check_interval // 60} minutes", inline=True)
            embed.add_field(name="Notify Movies", value="Yes" if self.notify_movies else "No", inline=True)
            embed.add_field(name="Notify New Shows", value="Yes" if self.notify_new_shows else "No", inline=True)
            embed.add_field(name="Notify Recent Episodes", value="Yes" if self.notify_recent_episodes else "No", inline=True)
            embed.add_field(name="Recent Episode Days", value=str(self.recent_episode_days), inline=True)
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
            embed.add_field(
                name="Discord Connection",
                value="✅ Connected",
                inline=False
            )
            
            # Check Plex connection
            plex_connected = self.plex_monitor.connect()
            if plex_connected:
                embed.add_field(
                    name="Plex Connection",
                    value=f"✅ Connected to {self.plex_monitor.plex_url}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Plex Connection",
                    value="❌ Failed to connect to Plex server",
                    inline=False
                )
            
            # Check libraries
            if plex_connected:
                movie_library = self.plex_monitor.get_library(self.movie_library)
                if movie_library:
                    embed.add_field(
                        name=f"{self.movie_library} Library",
                        value="✅ Available",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name=f"{self.movie_library} Library",
                        value="❌ Not found",
                        inline=True
                    )
                
                tv_library = self.plex_monitor.get_library(self.tv_library)
                if tv_library:
                    embed.add_field(
                        name=f"{self.tv_library} Library",
                        value="✅ Available",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name=f"{self.tv_library} Library",
                        value="❌ Not found",
                        inline=True
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
        
        # Run the bot
        await self.bot.start(self.token)
        
    async def _check_for_new_media(self, manual: bool = False):
        """Check for new media and send Discord notifications."""
        if not self.bot.is_ready():
            logger.warning("Bot not ready, skipping media check")
            return

        logger.info("Checking for new media...")
        
        # Get the notification channel
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Could not find channel with ID {self.channel_id}")
            return

        new_items = []
        
        # Check for new movies
        if self.notify_movies:
            movies = self.plex_monitor.get_recently_added_movies(days=1)
            for movie in movies:
                if movie["key"] not in self.processed_media:
                    new_items.append(movie)
                    self.processed_media.add(movie["key"])
        
        # Check for new TV episodes
        if self.notify_new_shows or self.notify_recent_episodes:
            episodes = self.plex_monitor.get_recently_added_episodes(days=1)
            
            # Group episodes by show
            shows = {}
            show_is_new = {}
            
            for episode in episodes:
                if episode["key"] not in self.processed_media:
                    show_title = episode["show_title"]
                    
                    # Check if this is a new show (first episode of first season)
                    is_first_episode = episode["season_number"] == 1 and episode["episode_number"] == 1
                    
                    # Track if this show is new to the server
                    if is_first_episode:
                        show_is_new[show_title] = True
                    
                    # Check if the episode recently aired (if it has an air date)
                    recently_aired = False
                    if episode.get("air_date"):
                        try:
                            air_date = datetime.fromisoformat(episode["air_date"])
                            recently_aired = (datetime.now() - air_date).days <= self.recent_episode_days
                        except (ValueError, TypeError):
                            recently_aired = False
                    
                    # Only add episodes that match our notification criteria
                    should_add = False
                    
                    # Add if it's a new show and we're notifying for new shows
                    if self.notify_new_shows and show_is_new.get(show_title, False):
                        should_add = True
                    
                    # Add if it recently aired and we're notifying for recent episodes
                    if self.notify_recent_episodes and recently_aired:
                        should_add = True
                    
                    if should_add:
                        if show_title not in shows:
                            shows[show_title] = []
                        shows[show_title].append(episode)
                    
                    # Mark as processed regardless
                    self.processed_media.add(episode["key"])
            
            # Add grouped episodes to new items
            for show_title, show_episodes in shows.items():
                if len(show_episodes) == 1:
                    new_items.append(show_episodes[0])
                else:
                    # Create a group item
                    first_ep = show_episodes[0]
                    group_item = {
                        "type": "tv_group",
                        "show_title": show_title,
                        "episodes": show_episodes,
                        "poster_url": first_ep.get("show_poster_url"),
                        "is_new_show": show_is_new.get(show_title, False)
                    }
                    new_items.append(group_item)
        
        # Send notifications for new items
        for item in new_items:
            if item["type"] == "movie":
                embed = self._create_movie_embed(item)
                await channel.send(embed=embed)
            elif item["type"] == "episode":
                embed = self._create_episode_embed(item)
                await channel.send(embed=embed)
            elif item["type"] == "tv_group":
                embed = self._create_episode_group_embed(item)
                await channel.send(embed=embed)
        
        # Save processed media to file
        save_processed_media(self.processed_media, self.data_file)
        
        if new_items:
            logger.info(f"Sent notifications for {len(new_items)} new items")
        else:
            logger.info("No new media found")

    def _create_movie_embed(self, movie: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for a movie."""
        embed = discord.Embed(
            title=f"New Movie Added: {movie['title']} ({movie.get('year', 'N/A')})",
            description=movie.get("summary", "No summary available"),
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        
        if movie.get("poster_url"):
            embed.set_thumbnail(url=movie["poster_url"])
            
        if movie.get("content_rating"):
            embed.add_field(name="Rating", value=movie["content_rating"], inline=True)
            
        if movie.get("rating"):
            embed.add_field(name="Score", value=f"{movie['rating']}/10", inline=True)
            
        if movie.get("duration"):
            embed.add_field(name="Duration", value=format_duration(movie["duration"]), inline=True)
            
        if movie.get("genres"):
            embed.add_field(name="Genres", value=", ".join(movie["genres"]), inline=True)
            
        if movie.get("directors"):
            embed.add_field(name="Director", value=", ".join(movie["directors"]), inline=True)
            
        if movie.get("actors"):
            embed.add_field(name="Cast", value=", ".join(movie["actors"]), inline=True)
            
        embed.set_footer(text="Plex Media Server")
        
        return embed
        
    def _create_episode_embed(self, episode: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for a TV episode."""
        is_new_show = episode["season_number"] == 1 and episode["episode_number"] == 1
        
        if is_new_show:
            title = f"New Show Added: {episode['show_title']}"
        else:
            title = f"New Episode Added: {episode['show_title']}"
            
        description = f"**S{episode['season_number']}E{episode['episode_number']} - {episode['title']}**\n\n{episode.get('summary', 'No summary available')}"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        
        if episode.get("poster_url"):
            embed.set_thumbnail(url=episode["poster_url"])
        elif episode.get("show_poster_url"):
            embed.set_thumbnail(url=episode["show_poster_url"])
            
        if episode.get("content_rating"):
            embed.add_field(name="Rating", value=episode["content_rating"], inline=True)
            
        if episode.get("duration"):
            embed.add_field(name="Duration", value=format_duration(episode["duration"]), inline=True)
            
        if episode.get("air_date"):
            embed.add_field(name="Air Date", value=episode["air_date"], inline=True)
            
        embed.set_footer(text="Plex Media Server")
        
        return embed
        
    def _create_episode_group_embed(self, group: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for a group of TV episodes."""
        episodes = group["episodes"]
        show_title = group["show_title"]
        is_new_show = group.get("is_new_show", False)
        
        if is_new_show:
            title = f"New Show Added: {show_title}"
        else:
            title = f"New Episodes Added: {show_title}"
            
        description = "**Episodes:**\n"
        
        for episode in episodes:
            description += f"• S{episode['season_number']}E{episode['episode_number']} - {episode['title']}"
            if episode.get("air_date"):
                description += f" (Aired: {episode['air_date']})"
            description += "\n"
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        
        if group.get("poster_url"):
            embed.set_thumbnail(url=group["poster_url"])
            
        embed.add_field(name="Total Episodes", value=str(len(episodes)), inline=True)
        
        if is_new_show:
            embed.add_field(name="New Series", value="✅", inline=True)
        
        embed.set_footer(text="Plex Media Server")
        
        return embed

# For backward compatibility
DiscordBot = PlexDiscordBot
