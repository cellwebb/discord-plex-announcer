"""Media storage utilities for tracking processed media items."""

import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("plex_discord_bot")


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
        logger.debug(f"Saved check timestamp {timestamp.isoformat()} to {timestamp_file}")
    except IOError as e:
        logger.error(f"Error saving check timestamp: {e}")
