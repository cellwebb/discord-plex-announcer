#!/usr/bin/env python3
"""Healthcheck command-line script for Plex Discord Announcer."""

import asyncio
import sys
from plex_announcer.utils.healthcheck import run_healthcheck


if __name__ == "__main__":
    # Run the healthcheck and return appropriate exit code
    success = asyncio.run(run_healthcheck())
    sys.exit(0 if success else 1)
