"""Formatting utilities for Plex Discord announcer."""


def format_duration(milliseconds: int) -> str:
    """Format duration from milliseconds to human-readable string."""
    total_seconds = milliseconds // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"
