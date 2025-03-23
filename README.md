# Plex Discord Announcer

A Discord bot that sends notifications to Discord when new media is added to your Plex server.

## Features

- Monitors Plex libraries for new movies and TV shows
- Sends formatted announcements to a Discord channel
- Separate notification options for new TV shows and recently aired episodes
- Configurable timeframe for considering episodes as "recently aired"
- Groups episodes from the same show to reduce notification clutter
- Rich Discord embeds with media details and metadata
- Admin commands for status, health checks and manual refresh
- Comprehensive logging with file rotation
- Built-in healthcheck system for monitoring
- Docker support with healthcheck integration

## Installation

### Requirements

- Python 3.8+
- A Discord bot token and server with appropriate permissions
- A Plex Media Server with API access

### Standard Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/discord-plex-announcer.git
cd discord-plex-announcer
```

1. Create a virtual environment and install dependencies:

```bash
make setup
```

1. Configure the bot by copying the example environment file:

```bash
cp .env.example .env
```

1. Edit the `.env` file with your Discord token, channel ID, and Plex server details.
1. Run the bot:

```bash
make run
```

### Docker Installation

1. Configure your environment variables in the `.env` file.
1. Build and run with Docker Compose:

```bash
docker-compose up -d
```

## Configuration

Configuration is done via environment variables:

| Variable               | Description                                        | Default                   |
| ---------------------- | -------------------------------------------------- | ------------------------- |
| DISCORD_TOKEN          | Your Discord bot token                             | (required)                |
| CHANNEL_ID             | Discord channel ID for announcements               | (required)                |
| PLEX_URL               | URL of your Plex server                            | `http://localhost:32400`  |
| PLEX_TOKEN             | Your Plex authentication token                     | (required)                |
| CHECK_INTERVAL         | How often to check for new media (in seconds)      | 3600                      |
| MOVIE_LIBRARY          | Name of your Plex movie library                    | Movies                    |
| TV_LIBRARY             | Name of your Plex TV library                       | TV Shows                  |
| NOTIFY_MOVIES          | Whether to notify for new movies                   | true                      |
| NOTIFY_NEW_SHOWS       | Whether to notify for new TV shows (first episode) | true                      |
| NOTIFY_RECENT_EPISODES | Whether to notify for recently aired episodes      | true                      |
| RECENT_EPISODE_DAYS    | Days to consider an episode as "recently aired"    | 30                        |
| DATA_FILE              | Path to store processed media data                 | data/processed_media.json |
| LOGGING_LEVEL          | Log level (DEBUG, INFO, WARNING, ERROR)            | INFO                      |
| PLEX_CONNECT_RETRY     | Number of retries for Plex connection              | 3                         |

## Usage

### Running the Bot

You have multiple ways to run the bot:

```bash
# Using the Makefile (recommended)
make run

# Directly as a Python module
python -m plex_announcer

# Using the run script
python run.py
```

### Discord Commands

The bot responds to the following commands:

- `!check` - Manually check for new media
- `!status` - View the bot's status and configuration
- `!healthcheck` - Check connectivity to Discord and Plex

### Healthcheck

The application includes a built-in healthcheck system to verify connectivity:

```bash
# Run the healthcheck
python healthcheck.py
```

This will check:

- Discord connectivity
- Plex server connectivity
- Data file accessibility

## Development

### Project Structure

```text
plex_announcer/
├── core/              # Core functionality
│   ├── discord_bot.py # Discord bot implementation
│   └── plex_monitor.py # Plex server monitoring
├── utils/             # Utility functions
│   ├── formatting.py  # Text formatting utilities
│   ├── media_storage.py # Media data persistence
│   ├── logging_config.py # Logging configuration
│   └── healthcheck.py # Healthcheck utilities
└── tests/             # Test suite
```

### Directory Structure

The application uses the following directories:

- `data/` - For persistent data storage (processed media information)
- `logs/` - For application logs with automatic rotation

### Running Tests

```bash
make test
```

For test coverage:

```bash
make test-cov
```

### Code Style

This project uses:

- flake8 for linting: `make lint`
- black for formatting: `make format`
- pre-commit hooks for consistency: `make pre-commit`

### Docker

The Docker setup includes:

- Proper volume mapping for data and logs
- Built-in healthcheck
- Environment variable handling with sensible defaults

Monitor container health:

```bash
docker inspect --format="{{.State.Health.Status}}" plex-discord-bot
```

## License

MIT License - See LICENSE file for details.

## Version Information and Release Plan

### Current Version

**Version 0.2.0** - See [CHANGELOG.md](CHANGELOG.md) for detailed release notes.

### Release Plan

#### Upcoming in v0.3.0

- Improved error handling for Plex API timeouts and connection issues
- Support for custom notification templates
- Enhanced filtering options for TV show notifications
- Web UI for configuration and monitoring

#### Future Roadmap

- **v0.4.0**: Integration with additional media servers (Jellyfin, Emby)
- **v0.5.0**: Advanced notification rules and scheduling
- **v1.0.0**: Stable release with complete feature set and comprehensive documentation

### Upgrading

When upgrading to a new version:

1. Check the [CHANGELOG.md](CHANGELOG.md) for breaking changes
2. Back up your `.env` file and `data` directory
3. Pull the latest code or update your Docker image
4. Update your configuration if new environment variables were added
5. Restart the bot

```bash
# For Docker installations
docker-compose pull
docker-compose up -d

# For standard installations
git pull
make setup
make run
```
