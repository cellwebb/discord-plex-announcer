# Plex Discord Bot

A Discord bot that notifies your server when new movies and TV shows are added to your Plex library.

## Features

- Posts notifications to a Discord channel when new movies and TV shows are added to Plex
- Includes media details like rating, genres, directors, and actors
- Displays movie/episode poster thumbnails in notifications
- Customizable check interval (default: 1 hour)
- Keeps track of processed media to avoid duplicate notifications
- Simple commands for manual checks and status updates
- Built-in health monitoring and error handling
- Consolidated TV episode notifications (one message per show)

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

### Synology NAS Deployment

To deploy on a Synology NAS using Docker Container Manager:

1. **Prerequisites**:

   - Install Docker package from Synology Package Center
   - Enable SSH on your Synology (Control Panel → Terminal & SNMP → Enable SSH)

2. **Installation Steps**:

   - Connect to your Synology via SSH: `ssh username@synology_ip`
   - Create a directory for the bot: `mkdir -p /volume1/docker/plex-discord-bot`
   - Navigate to the directory: `cd /volume1/docker/plex-discord-bot`
   - Download the repository files:

     ```bash
     curl -L https://github.com/your-username/discord-plex-announcer/archive/refs/heads/main.zip -o main.zip
     unzip main.zip
     mv discord-plex-announcer-main/* .
     rm -rf discord-plex-announcer-main main.zip
     ```

   - Copy and edit the environment file: `cp .env.example .env`
   - Edit the .env file with your values: `vi .env`

3. **Launch in Docker Container Manager**:

   - Open Docker Container Manager in DSM
   - Go to "Registry" → Search for "plex-discord-bot" (if you've pushed the image to Docker Hub) OR
   - Go to "Image" → "Add" → "Add From URL" → Enter the GitHub repository URL
   - Alternatively, use "Container" → "Create" → "Import from docker-compose.yml" and browse to the docker-compose.yml file in your created directory

4. **Volume Mapping**:

   - Map `/volume1/docker/plex-discord-bot` to `/app` inside the container to persist data

5. **Environment Variables**:
   - Ensure all required environment variables from the .env file are added to the container configuration

For troubleshooting, check the container logs through the Docker Container Manager interface.

## Manual Installation

If you prefer not to use Docker:

1. Clone this repository
2. Set up a virtual environment and install dependencies using the Makefile:

   ```bash
   make setup
   source venv/bin/activate
   ```

   Or install dependencies directly:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your configuration
4. Run the bot:

   ```bash
   # Using the Makefile
   make run
   
   # Or directly
   python plex_discord_bot.py
   ```

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Development

This project includes a Makefile to streamline common development tasks:

```bash
# Show all available commands
make help

# Set up development environment (creates venv and installs dependencies)
make setup

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint code with flake8
make lint

# Format code with black
make format

# Build Docker image
make docker-build

# Run with Docker
make docker-run

# View Docker logs
make docker-logs

# Stop Docker container
make docker-stop

# Clean up (removes venv and cache files)
make clean
```

The project also includes pre-commit hooks for code quality. After installing dependencies, set up pre-commit with:

```bash
pre-commit install
```

## Configuration

Configuration can be done via environment variables or command line arguments:

| Environment Variable  | Command Line Argument | Description                                                   |
| --------------------- | --------------------- | ------------------------------------------------------------- |
| `DISCORD_TOKEN`       | `--token`             | Discord bot token                                             |
| `CHANNEL_ID`          | `--channel`           | Discord channel ID for notifications                          |
| `PLEX_URL`            | `--plex-url`          | URL of your Plex server (default: `http://localhost:32400`)   |
| `PLEX_TOKEN`          | `--plex-token`        | Plex authentication token                                     |
| `MOVIE_LIBRARY`       | `--movie-library`     | Name of the Plex movie library (default: Movies)              |
| `TV_LIBRARY`          | `--tv-library`        | Name of the Plex TV show library (default: TV Shows)          |
| `NOTIFY_MOVIES`       | `--notify-movies`     | Enable/disable movie notifications (default: true)            |
| `NOTIFY_TV`           | `--notify-tv`         | Enable/disable TV show notifications (default: true)          |
| `CHECK_INTERVAL`      | `--interval`          | Check interval in seconds (default: 3600 - 1 hour)           |
| `DATA_FILE`           | `--data-file`         | File to store processed media (default: processed_media.json) |
| `PLEX_CONNECT_RETRY`  | `--retry`             | Number of Plex connection retries (default: 3)                |
| `LOGGING_LEVEL`       | N/A                   | Logging level (default: INFO)                                 |

## Commands

- `!checkplex` - Force a check for new media
- `!status` - Display bot status and configuration
- `!healthcheck` - Verify connectivity to Plex and Discord

## Testing

The project uses pytest for testing. To run tests:

```bash
python -m pytest
```

To run tests with coverage reports:

```bash
python -m pytest --cov=. --cov-report=term
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
