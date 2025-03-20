# Plex Discord Bot

A Discord bot that notifies your server when new movies and TV shows are added to your Plex library.

## Features

- 🎬 Posts notifications to a Discord channel when new movies are added to Plex
- 📺 Sends alerts for new TV show episodes
- 📊 Includes media details like rating, genres, directors, and actors
- 🖼️ Displays movie/episode poster thumbnails in notifications
- ⏱️ Customizable check interval
- 💾 Keeps track of processed media to avoid duplicate notifications
- 🤖 Simple commands for manual checks and status updates
- 🛡️ Built-in health monitoring and error handling
- 🔄 Automatic grouping of multiple TV episodes from the same show

## Requirements

- Discord Bot Token
- Plex Media Server with API access
- Discord server with a channel for notifications

## Quick Start (Docker - Recommended)

The easiest and recommended way to run the bot is with Docker Compose:

1. Clone this repository
2. Copy `.env.example` to `.env` and fill in your configuration
3. Run the bot:

   ```bash
   docker-compose up -d
   ```

This method handles all dependencies and ensures a clean, isolated environment for the bot.

## Manual Installation

If you prefer not to use Docker:

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt` (requires Python 3.8+)
3. Copy `.env.example` to `.env` and fill in your configuration
4. Run the bot: `python plex_discord_bot.py`

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Configuration

Configuration can be done via environment variables or command line arguments:

| Environment Variable   | Command Line Argument | Description                                                      |
| ---------------------- | --------------------- | ---------------------------------------------------------------- |
| `DISCORD_TOKEN`        | `--token`             | Discord bot token                                                |
| `CHANNEL_ID`           | `--channel`           | Discord channel ID for notifications                             |
| `PLEX_URL`             | `--plex-url`          | URL of your Plex server (default: `http://localhost:32400`)      |
| `PLEX_TOKEN`           | `--plex-token`        | Plex authentication token                                        |
| `MOVIE_LIBRARY`        | `--movie-library`     | Name of the Plex movie library (default: Movies)                 |
| `TV_LIBRARY`           | `--tv-library`        | Name of the Plex TV show library (default: TV Shows)             |
| `NOTIFY_MOVIES`        | `--notify-movies`     | Enable/disable movie notifications (default: true)               |
| `NOTIFY_TV`            | `--notify-tv`         | Enable/disable TV show notifications (default: true)             |
| `CHECK_INTERVAL`       | `--interval`          | Check interval in seconds (default: 300)                         |
| `DATA_FILE`            | `--data-file`         | File to store processed media (default: processed_media.json)    |
| `TV_SHOW_BUFFER_FILE`  | `--buffer-file`       | File to store TV buffer data (default: tv_show_buffer.json)      |
| `TV_BUFFER_TIME`       | `--buffer-time`       | Seconds to buffer TV episodes (default: 7200 - 2 hours)          |
| `PLEX_CONNECT_RETRY`   | `--retry`             | Number of Plex connection retries (default: 3)                   |
| `LOGGING_LEVEL`        | N/A                   | Logging level (default: INFO)                                    |

## Commands

- `!checkplex` - Force a check for new media
- `!status` - Display bot status and configuration
- `!healthcheck` - Verify connectivity to Plex and Discord

## Testing

Basic unit tests are included. To run tests:

```bash
python -m unittest test_plex_bot.py
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
