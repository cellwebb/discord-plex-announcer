"""Media storage utilities for tracking processed media items."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Set

logger = logging.getLogger("plex_discord_bot")


def load_processed_media(data_file: str) -> Set[str]:
    """Load the set of processed media keys from disk."""
    if os.path.exists(data_file):
        try:
            with open(data_file, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading processed media data: {e}")
            return set()
    else:
        logger.info(f"No existing data file found at {data_file}")
        return set()


def save_processed_media(media: Set[str], data_file: str) -> None:
    """Save the set of processed media keys to disk."""
    try:
        with open(data_file, "w") as f:
            json.dump(list(media), f)
        logger.debug(f"Saved {len(media)} processed media items to {data_file}")
    except IOError as e:
        logger.error(f"Error saving processed media data: {e}")


def load_last_check_time(timestamp_file: str) -> Optional[datetime]:
    """Load the timestamp of the last successful media check.
    Args:
        timestamp_file: Path to the timestamp file
    Returns:
        The datetime of the last check or None if no previous check
    """
    if os.path.exists(timestamp_file):
        try:
            with open(timestamp_file, "r") as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
        except (ValueError, IOError) as e:
            logger.error(f"Error loading last check timestamp: {e}")
            return None
    else:
        logger.info(f"No existing timestamp file found at {timestamp_file}")
        return None


def save_last_check_time(timestamp: datetime, timestamp_file: str) -> None:
    """Save the timestamp of the last successful media check.
    Args:
        timestamp: The datetime to save
        timestamp_file: Path to the timestamp file
    """
    try:
        with open(timestamp_file, "w") as f:
            f.write(timestamp.isoformat())
        logger.debug(
            f"Saved check timestamp {timestamp.isoformat()} to {timestamp_file}"
        )
    except IOError as e:
        logger.error(f"Error saving check timestamp: {e}")
