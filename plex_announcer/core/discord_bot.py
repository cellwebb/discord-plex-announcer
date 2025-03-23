"""
Discord bot implementation for sending Plex media notifications.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set

import discord
from discord.ext import commands, tasks

from plex_announcer.utils.media_storage import load_processed_media, save_processed_media
from plex_announcer.utils.formatting import format_duration

logger = logging.getLogger("plex_discord_bot")


class PlexDiscordBot(commands.Bot):
    """Discord bot for sending Plex media notifications."""

    def __init__(
        self,
        command_prefix: str,
        intents: discord.Intents,
        channel_id: int,
        plex_monitor,
        movie_library: str,
        tv_library: str,
        notify_movies: bool,
        notify_tv: bool,
        check_interval: int,
        data_file: str,
    ):
        """Initialize the Discord bot with configuration settings."""
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.channel_id = channel_id
        self.plex_monitor = plex_monitor
        self.movie_library = movie_library
        self.tv_library = tv_library
        self.notify_movies = notify_movies
        self.notify_tv = notify_tv
        self.check_interval = check_interval
        self.data_file = data_file
        self.processed_media: Set[str] = set()
        self.start_time: float = time.time()
        
        # Register commands
        self.add_commands()
        
        # Load processed media from storage
        self.processed_media = load_processed_media(self.data_file)

    def add_commands(self):
        """Register bot commands."""
        
        @self.command(name="check")
        async def check_plex(ctx: commands.Context):
            """Discord command to manually check for new media."""
            if not ctx.guild:
                await ctx.send("This command can only be used in a server.")
                return

            await ctx.send("Manually checking for new media...")
            await self.check_for_new_media(manual=True)
            await ctx.send("Check completed!")

        @self.command(name="status")
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
            embed.add_field(name="Notify TV", value="Yes" if self.notify_tv else "No", inline=True)
            embed.add_field(name="Media Entries", value=str(len(self.processed_media)), inline=True)
            
            await ctx.send(embed=embed)

        @self.command(name="healthcheck")
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

    async def setup_hook(self):
        """Set up hook for Discord bot."""
        self.check_task.start()
        logger.info("Automated media check scheduled")

    @tasks.loop(seconds=1)
    async def check_task(self):
        """Task to periodically check for new media."""
        await self.wait_until_ready()
        self.check_task.change_interval(seconds=self.check_interval)
        await self.check_for_new_media()

    async def check_for_new_media(self, manual: bool = False):
        """Check for new media and send Discord notifications."""
        if not self.is_ready():
            logger.warning("Bot not ready, skipping media check")
            return

        logger.info("Checking for new media...")
        
        # Get the notification channel
        channel = self.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Could not find channel with ID {self.channel_id}")
            return

        new_items = []
        
        # Check for new movies
        if self.notify_movies:
            movies = self.plex_monitor.get_recently_added_movies(self.movie_library, days=1)
            for movie in movies:
                if movie["key"] not in self.processed_media:
                    new_items.append(movie)
                    self.processed_media.add(movie["key"])
        
        # Check for new TV episodes
        if self.notify_tv:
            episodes = self.plex_monitor.get_recently_added_episodes(self.tv_library, days=1)
            
            # Group episodes by show
            shows: Dict[str, List[Dict]] = {}
            for episode in episodes:
                if episode["key"] not in self.processed_media:
                    show_title = episode["show_title"]
                    if show_title not in shows:
                        shows[show_title] = []
                    shows[show_title].append(episode)
                    self.processed_media.add(episode["key"])
            
            # Create grouped notifications
            for show_title, show_episodes in shows.items():
                if not show_episodes:
                    continue
                
                # Sort episodes by season and episode number
                show_episodes.sort(
                    key=lambda ep: (ep["season_number"], ep["episode_number"])
                )
                
                # Only notify for shows with recent air dates or first episodes of new shows
                recent_threshold = datetime.now().date() - datetime.timedelta(days=30)
                is_recent = any(
                    ep.get("air_date") and ep["air_date"] > recent_threshold
                    for ep in show_episodes
                )
                is_new_show = show_episodes[0]["season_number"] == 1 and show_episodes[0]["episode_number"] == 1
                
                if is_recent or is_new_show:
                    # Create a custom item for the grouped episodes
                    group_item = {
                        "type": "tv_group",
                        "show_title": show_title,
                        "episodes": show_episodes,
                        "count": len(show_episodes),
                        "poster_url": show_episodes[0].get("show_poster_url"),
                    }
                    new_items.append(group_item)
        
        # Save the updated processed media list
        save_processed_media(self.processed_media, self.data_file)
        
        # Send notifications for new items
        for item in new_items:
            await self._send_notification(channel, item)
        
        if not new_items and manual:
            await channel.send("No new media found.")
        
        logger.info(f"Media check complete. Found {len(new_items)} new items.")

    async def _send_notification(self, channel, item):
        """Send a notification for a media item."""
        if item["type"] == "movie":
            embed = self._create_movie_embed(item)
        elif item["type"] == "tv_group":
            embed = self._create_episode_group_embed(item)
        else:
            logger.warning(f"Unknown item type: {item['type']}")
            return
        
        await channel.send(embed=embed)

    def _create_movie_embed(self, movie):
        """Create Discord embed for movie notification."""
        embed = discord.Embed(
            title=f"{movie['title']} ({movie['year']})",
            description=movie["summary"],
            color=discord.Color.blue(),
        )
        
        embed.set_author(name="New Movie Added to Plex")
        
        if movie.get("poster_url"):
            embed.set_thumbnail(url=movie["poster_url"])
        
        if movie.get("content_rating"):
            embed.add_field(name="Rating", value=movie["content_rating"], inline=True)
        
        if movie.get("duration"):
            embed.add_field(
                name="Duration", 
                value=format_duration(movie["duration"]), 
                inline=True
            )
        
        if movie.get("genres"):
            embed.add_field(
                name="Genres", 
                value=", ".join(movie["genres"][:3]), 
                inline=True
            )
        
        if movie.get("directors"):
            embed.add_field(
                name="Director", 
                value=", ".join(movie["directors"][:2]), 
                inline=True
            )
        
        if movie.get("actors"):
            embed.add_field(
                name="Starring", 
                value=", ".join(movie["actors"][:3]), 
                inline=True
            )
        
        embed.set_footer(text="Plex Media Server")
        
        return embed

    def _create_episode_group_embed(self, group):
        """Create Discord embed for a group of TV episodes."""
        embed = discord.Embed(
            title=f"{group['show_title']}",
            description=f"{group['count']} new episode{'s' if group['count'] > 1 else ''} added",
            color=discord.Color.green(),
        )
        
        embed.set_author(name="New TV Content Added to Plex")
        
        if group.get("poster_url"):
            embed.set_thumbnail(url=group["poster_url"])
        
        # Add episode details
        for i, episode in enumerate(group["episodes"][:5]):  # Limit to 5 episodes to avoid overly long embeds
            season_episode = f"S{episode['season_number']:02d}E{episode['episode_number']:02d}"
            embed.add_field(
                name=f"{season_episode}: {episode['title']}",
                value=episode.get("summary", "No summary available")[:100] + "..." 
                if episode.get("summary") and len(episode.get("summary", "")) > 100 
                else episode.get("summary", "No summary available"),
                inline=False,
            )
        
        # If there are more episodes than shown
        if len(group["episodes"]) > 5:
            embed.add_field(
                name="More Episodes",
                value=f"+ {len(group['episodes']) - 5} more episode(s)",
                inline=False,
            )
        
        embed.set_footer(text="Plex Media Server")
        
        return embed
