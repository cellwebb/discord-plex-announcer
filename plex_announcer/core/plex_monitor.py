"""
Module for monitoring Plex Media Server for new content.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from plexapi.exceptions import NotFound, Unauthorized
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie

logger = logging.getLogger("plex_discord_bot")


class PlexMonitor:
    """Handles connection to Plex server and retrieves information about media libraries."""

    def __init__(
        self,
        base_url: str,
        token: str,
        movie_library: str = "Movies",
        tv_library: str = "TV Shows",
        connect_retry: int = 3,
    ):
        """Initialize the Plex monitor with server URL and authentication token."""
        self.plex_url: str = base_url
        self.plex_token: str = token
        self.movie_library: str = movie_library
        self.tv_library: str = tv_library
        self.plex: Optional[PlexServer] = None
        self.connect_retry: int = connect_retry
        self.connect()

    def connect(self) -> bool:
        """Establish connection to the Plex server."""
        logger.info(f"Connecting to Plex server at {self.plex_url}")
        
        for attempt in range(self.connect_retry):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{self.connect_retry}")
                self.plex = PlexServer(self.plex_url, self.plex_token)
                logger.info(f"Successfully connected to Plex server: {self.plex.friendlyName}")
                return True
            except Unauthorized as e:
                logger.error(f"Authentication failed for Plex server: {e}")
                return False
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Failed to connect to Plex server: {e}")
                if attempt < self.connect_retry - 1:
                    logger.info(f"Retrying in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Failed to connect to Plex server: {e}")
                if attempt < self.connect_retry - 1:
                    logger.info(f"Retrying in 5 seconds...")
                    time.sleep(5)
        
        logger.error(f"Failed to connect to Plex server after {self.connect_retry} attempts")
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

    def get_recently_added_movies(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get movies added to Plex within the specified time period."""
        if not self.plex:
            if not self.connect():
                return []

        try:
            library = self.get_library(self.movie_library)
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

    def get_recently_added_episodes(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get TV episodes added to Plex within the specified time period."""
        if not self.plex:
            if not self.connect():
                return []

        try:
            library = self.get_library(self.tv_library)
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
                    if hasattr(episode.show(), "thumb") and episode.show().thumb:
                        show_poster_url = (
                            f"{self.plex_url}{episode.show().thumb}?X-Plex-Token={self.plex_token}"
                        )
                    
                    # Get air date if available
                    air_date = None
                    if hasattr(episode, "originallyAvailableAt") and episode.originallyAvailableAt:
                        air_date = episode.originallyAvailableAt.isoformat()

                    new_episodes.append(
                        {
                            "type": "episode",
                            "key": episode.key,
                            "title": episode.title,
                            "show_title": episode.show().title,
                            "season_number": episode.seasonNumber,
                            "episode_number": episode.index,
                            "added_at": episode.addedAt.isoformat(),
                            "air_date": air_date,
                            "summary": episode.summary,
                            "content_rating": getattr(
                                episode.show(), "contentRating", "Not Rated"
                            ),
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
