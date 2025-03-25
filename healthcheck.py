#!/usr/bin/env python3
"""
Healthcheck script for the Plex Discord Announcer.
Verifies that the bot can connect to both Discord and Plex.
"""

import logging
import os
import sys

from dotenv import load_dotenv

from plex_announcer.core.plex_monitor import PlexMonitor

# Configure minimal logging
logging.basicConfig(level=logging.ERROR)


def main():
    """Run healthcheck to verify connections."""
    # Load environment variables
    load_dotenv()

    # Check for required environment variables
    plex_base_url = os.getenv("PLEX_BASE_URL")
    plex_token = os.getenv("PLEX_TOKEN")

    if not plex_base_url or not plex_token:
        print("ERROR: Missing required Plex configuration")
        sys.exit(1)

    # Try to connect to Plex
    try:
        plex_monitor = PlexMonitor(
            plex_base_url=plex_base_url, plex_token=plex_token, connect_retry=1
        )

        if not plex_monitor.connect():
            print("ERROR: Failed to connect to Plex server")
            sys.exit(1)

        print("Healthcheck passed: Successfully connected to Plex")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Healthcheck failed - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
