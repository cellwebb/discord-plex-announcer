"""
Utility for creating Discord embeds for Plex media.
"""

import logging
from datetime import datetime
from typing import Any, Dict

import discord

from plex_announcer.utils.formatting import format_duration

logger = logging.getLogger("plex_discord_bot")


class EmbedBuilder:
    """Builder for Discord embeds for Plex media."""

    @staticmethod
    def create_movie_embed(movie: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for a movie."""
        title = f"New Movie Added: {movie['title']}"
        if movie.get("year"):
            title += f" ({movie['year']})"

        description = movie.get("summary", "No summary available")

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        if movie.get("poster_url"):
            embed.set_thumbnail(url=movie["poster_url"])

        if movie.get("content_rating"):
            embed.add_field(name="Rating", value=movie["content_rating"], inline=True)

        if movie.get("duration"):
            embed.add_field(name="Duration", value=format_duration(movie["duration"]), inline=True)

        if movie.get("genres"):
            embed.add_field(name="Genres", value=", ".join(movie["genres"]), inline=True)

        embed.set_footer(text="Plex Media Server")

        return embed

    @staticmethod
    def create_episode_embed(episode: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for a TV episode."""
        is_first_episode = episode["season_number"] == 1 and episode["episode_number"] == 1
        show_title = episode["show_title"]

        if is_first_episode:
            title = f"New Show Added: {show_title}"
        else:
            title = f"New Episode Added: {show_title}"

        episode_info = (
            f"**S{episode['season_number']}E{episode['episode_number']} - {episode['title']}**"
        )
        summary = episode.get("summary", "No summary available")
        description = f"{episode_info}\n\n{summary}"

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
            embed.add_field(
                name="Duration", value=format_duration(episode["duration"]), inline=True
            )

        if episode.get("air_date"):
            embed.add_field(name="Air Date", value=episode["air_date"], inline=True)

        embed.set_footer(text="Plex Media Server")

        return embed
