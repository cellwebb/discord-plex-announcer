"""
Module for monitoring Plex Media Server for new content.
"""

import logging
import socket
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from plexapi.exceptions import NotFound, Unauthorized
from plexapi.library import LibrarySection
from plexapi.server import PlexServer
from plexapi.video import Episode, Movie
from requests.exceptions import ConnectionError, ReadTimeout

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
        self.plex_base_url: str = base_url
        self.plex_token: str = token
        self.movie_library: str = movie_library
        self.tv_library: str = tv_library
        self.plex: Optional[PlexServer] = None
        self.connect_retry: int = connect_retry
        self.connect()

    def connect(self) -> bool:
        """Establish connection to the Plex server."""
        logger.info(f"Connecting to Plex server at {self.plex_base_url}")

        for attempt in range(self.connect_retry):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{self.connect_retry}")
                # Set timeout for initial connection only
                self.plex = PlexServer(self.plex_base_url, self.plex_token, timeout=10)
                logger.info(
                    f"Successfully connected to Plex server: {self.plex.friendlyName}"
                )
                return True
            except Unauthorized as e:
                logger.error("Authentication failed for Plex server: %s", e)
                return False
            except (ConnectionError, ReadTimeout, socket.timeout) as e:
                logger.error("Failed to connect to Plex server: %s", e)
                if attempt < self.connect_retry - 1:
                    logger.info("Retrying in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                logger.error("Failed to connect to Plex server: %s", e)
                if attempt < self.connect_retry - 1:
                    logger.info("Retrying in 5 seconds...")
                    time.sleep(5)

        logger.error(
            "Failed to connect to Plex server after %s attempts", self.connect_retry
        )
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
            logger.error(f"Failed to find library '{library_name}'")
            return None
        except Exception as e:
            logger.error(f"Failed to find library '{library_name}': {e}")
            return None

    def get_recently_added_movies(
        self, since_datetime: Optional[datetime] = None, days: int = 1
    ) -> List[Dict[str, Any]]:
        """Get movies added to Plex within the specified time period.

        Args:
            since_datetime: Only return movies added after this datetime
            days: Number of days to look back if since_datetime is not provided

        Returns:
            List of movie dictionaries with metadata
        """
        if not self.plex:
            logger.error("Not connected to Plex server")
            return []

        try:
            library = self.get_library(self.movie_library)
            if not library:
                return []

            # Determine cutoff date based on parameters
            if since_datetime:
                cutoff_date = since_datetime
                logger.info(
                    f"Searching for movies added since {cutoff_date.isoformat()}"
                )
            else:
                cutoff_date = datetime.now() - timedelta(days=days)
                logger.info(f"Searching for movies added in the last {days} days")

            try:
                # Get all movies sorted by addedAt in descending order
                # Explicitly specify only valid filter fields
                recent_movies: List[Movie] = library.search(
                    libtype="movie", sort="addedAt:desc"
                )
            except (ConnectionError, ReadTimeout, socket.timeout) as e:
                logger.error("Error getting recently added movies: %s", e)
                return []
            except Exception as e:
                logger.error("Error getting recently added movies: %s", e)
                return []

            new_movies: List[Dict[str, Any]] = []
            for movie in recent_movies:
                try:
                    if movie.addedAt > cutoff_date:
                        poster_url: Optional[str] = None
                        if movie.thumb:
                            poster_url = f"{self.plex_base_url}{movie.thumb}?X-Plex-Token={self.plex_token}"

                        # Get movie attributes safely
                        content_rating = "Not Rated"
                        rating = None
                        genres = []

                        try:
                            if hasattr(movie, "contentRating"):
                                content_rating = movie.contentRating
                            if hasattr(movie, "rating"):
                                rating = movie.rating
                            if hasattr(movie, "genres"):
                                genres = [g.tag for g in movie.genres]
                        except (ConnectionError, ReadTimeout, socket.timeout) as e:
                            logger.error("Error getting movie metadata: %s", e)
                        except Exception as e:
                            logger.error("Error getting movie metadata: %s", e)

                        new_movies.append(
                            {
                                "type": "movie",
                                "key": movie.key,
                                "title": movie.title,
                                "year": movie.year,
                                "added_at": movie.addedAt.isoformat(),
                                "summary": movie.summary,
                                "content_rating": content_rating,
                                "rating": rating,
                                "poster_url": poster_url,
                                "genres": genres,
                            }
                        )
                    else:
                        # Since movies are sorted by addedAt, we can break early once we hit older movies  # noqa: E501
                        logger.debug(
                            f"Skipping older movies (added before {cutoff_date.isoformat()})"
                        )
                        break
                except Exception as e:
                    logger.error("Error processing movie: %s", e)
                    continue

            logger.info(
                f"Found {len(new_movies)} new movies since {cutoff_date.isoformat()}"
            )
            return new_movies
        except Exception as e:
            logger.error("Error getting recently added movies: %s", e)
            return []

    def get_recently_added_episodes(
        self, since_datetime: Optional[datetime] = None, days: int = 1
    ) -> List[Dict[str, Any]]:
        """Get TV episodes added to Plex within the specified time period.

        Args:
            since_datetime: Only return episodes added after this datetime
            days: Number of days to look back if since_datetime is not provided

        Returns:
            List of episode dictionaries with metadata
        """
        if not self.plex:
            logger.error("Not connected to Plex server")
            return []

        try:
            library = self.get_library(self.tv_library)
            if not library:
                return []

            # Determine cutoff date based on parameters
            if since_datetime:
                cutoff_date = since_datetime
                logger.info(
                    f"Searching for episodes added since {cutoff_date.isoformat()}"
                )
            else:
                cutoff_date = datetime.now() - timedelta(days=days)
                logger.info(f"Searching for episodes added in the last {days} days")

            try:
                # Get all episodes sorted by addedAt in descending order
                # Explicitly specify only valid filter fields
                recent_episodes: List[Episode] = library.searchEpisodes(
                    sort="addedAt:desc"
                )
            except (ConnectionError, ReadTimeout, socket.timeout) as e:
                logger.error("Error getting recently added episodes: %s", e)
                return []
            except Exception as e:
                logger.error("Error getting recently added episodes: %s", e)
                return []

            new_episodes: List[Dict[str, Any]] = []
            for episode in recent_episodes:
                try:
                    if episode.addedAt > cutoff_date:
                        poster_url: Optional[str] = None
                        if episode.thumb:
                            poster_url = f"{self.plex_base_url}{episode.thumb}?X-Plex-Token={self.plex_token}"  # noqa: E501

                        show_poster_url: Optional[str] = None
                        show = None
                        show_content_rating = "Not Rated"

                        try:
                            show = episode.show()
                            if hasattr(show, "thumb") and show.thumb:
                                show_poster_url = f"{self.plex_base_url}{show.thumb}?X-Plex-Token={self.plex_token}"  # noqa: E501
                            if hasattr(show, "contentRating"):
                                show_content_rating = show.contentRating
                        except (ConnectionError, ReadTimeout, socket.timeout) as e:
                            logger.error("Error getting show data for episode: %s", e)
                        except Exception as e:
                            logger.error("Error getting show data for episode: %s", e)

                        # Get air date if available
                        air_date = None
                        if (
                            hasattr(episode, "originallyAvailableAt")
                            and episode.originallyAvailableAt
                        ):
                            air_date = episode.originallyAvailableAt.isoformat()

                        new_episodes.append(
                            {
                                "type": "episode",
                                "key": episode.key,
                                "title": episode.title,
                                "show_title": episode.grandparentTitle,
                                "season": episode.parentIndex,
                                "episode": episode.index,
                                "season_number": episode.parentIndex,
                                "episode_number": episode.index,
                                "added_at": episode.addedAt.isoformat(),
                                "air_date": air_date,
                                "summary": episode.summary,
                                "content_rating": show_content_rating,
                                "poster_url": poster_url,
                                "show_poster_url": show_poster_url,
                                "duration": episode.duration,
                            }
                        )
                    else:
                        # Since episodes are sorted by addedAt, we can break early once we hit older episodes  # noqa: E501
                        logger.debug(
                            f"Skipping older episodes (added before {cutoff_date.isoformat()})"
                        )
                        break
                except Exception as e:
                    logger.error("Error processing episode: %s", e)
                    continue

            logger.info(
                f"Found {len(new_episodes)} new episodes since {cutoff_date.isoformat()}"
            )
            return new_episodes
        except Exception as e:
            logger.error("Error getting recently added episodes: %s", e)
            return []
