#!/usr/bin/env python3
"""Runner script for Plex Discord Announcer."""

import asyncio
from plex_announcer.__main__ import main

if __name__ == "__main__":
    asyncio.run(main())
