"""Media storage utilities for tracking processed media items."""

import json
import logging
import os
from typing import Set

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
