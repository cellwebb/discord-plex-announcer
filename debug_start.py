#!/usr/bin/env python3
"""
Debug startup script for Plex Discord Announcer.
"""

import logging
import os
import sys
import time
from datetime import datetime

# Configure direct logging to file
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="debug_log.txt",
    filemode="w",
)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger("").addHandler(console)

logger = logging.getLogger("debug_startup")


def main():
    """Debug startup function."""
    logger.info("Starting debug script at %s", datetime.now())

    # Log environment variables (except sensitive ones)
    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if any(sensitive in key for sensitive in ["TOKEN", "SECRET", "KEY"]):
            logger.info("%s: [REDACTED]", key)
        else:
            logger.info("%s: %s", key, value)

    # Start the actual bot in the background
    logger.info("Starting bot process...")
    if os.fork() == 0:  # Child process
        # Execute the real bot
        try:
            import asyncio

            from plex_announcer.cli import main as cli_main

            logger.info("Executing main function from plex_announcer.cli")
            asyncio.run(cli_main())
        except Exception as e:
            logger.error("Failed to start bot: %s", e, exc_info=True)
            sys.exit(1)
    else:  # Parent process
        logger.info("Bot started in background. Parent process will exit successfully.")

        # Sleep briefly to allow child process to start
        time.sleep(3)
        logger.info("Parent process exiting successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())
