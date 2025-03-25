#!/usr/bin/env python3
"""
Entry point script for running the Plex Discord Announcer.
"""

import asyncio

from plex_announcer.cli import main

if __name__ == "__main__":
    asyncio.run(main())
