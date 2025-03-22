# Discord Plex Announcer

A Discord bot that announces new movies and TV shows added to your Plex Media Server.

## 📋 Table of Contents

- [Discord Plex Announcer](#discord-plex-announcer)
  - [📋 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🚀 Quick Start](#-quick-start)
  - [🔧 Deployment Options](#-deployment-options)
    - [GitHub Container Registry (Recommended)](#github-container-registry-recommended)
      - [GitHub Container Registry Authentication](#github-container-registry-authentication)
    - [Docker Compose (Local Build)](#docker-compose-local-build)
    - [Synology NAS Deployment](#synology-nas-deployment)
    - [Manual Installation](#manual-installation)
  - [⚙️ Configuration](#️-configuration)
  - [💬 Commands](#-commands)
  - [🛠️ Development](#️-development)
  - [🧪 Testing](#-testing)
  - [📄 License](#-license)

## ✨ Features

- Automatic monitoring of Plex libraries for new content
- Discord announcements for new movies and TV shows
- Detailed metadata including title, summary, year, and genres
- Custom check intervals
- Configurable notification preferences
- Docker support for easy deployment

## 🚀 Quick Start

The fastest way to get started is to use the pre-built Docker image from GitHub Container Registry:

```bash
# Create a directory for the bot
mkdir -p plex-discord-bot && cd plex-discord-bot

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  plex-discord-bot:
    container_name: plex-discord-bot
    image: ghcr.io/cellwebb/discord-plex-announcer:latest
    restart: unless-stopped
    volumes:
      - ./:/app
    environment:
      - DISCORD_TOKEN=your_discord_token
      - CHANNEL_ID=your_channel_id
      - PLEX_URL=http://your_plex_server:32400
      - PLEX_TOKEN=your_plex_token
EOF

# Start the bot
docker-compose up -d
```

## 🔧 Deployment Options

### GitHub Container Registry (Recommended)

The simplest deployment method uses pre-built Docker images from GitHub Container Registry:

1. **Set up your environment**:

   ```bash
   mkdir -p plex-discord-bot && cd plex-discord-bot

   # Create a .env file with your configuration
   cat > .env << 'EOF'
   DISCORD_TOKEN=your_discord_token
   CHANNEL_ID=your_channel_id
   PLEX_URL=http://your_plex_server:32400
   PLEX_TOKEN=your_plex_token
   EOF

   # Download the deployment docker-compose file
   curl -O https://raw.githubusercontent.com/cellwebb/discord-plex-announcer/main/docker-compose.deploy.yml
   ```

2. **Deploy and run the bot**:

   ```bash
   docker-compose -f docker-compose.deploy.yml up -d
   ```

3. **Update to the latest version**:

   ```bash
   docker-compose -f docker-compose.deploy.yml pull
   docker-compose -f docker-compose.deploy.yml up -d
   ```

#### GitHub Container Registry Authentication

If you encounter authentication issues when pulling the image:

1. Create a GitHub Personal Access Token with the `read:packages` scope at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)

2. Log in to the GitHub Container Registry:

   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```

   Replace `USERNAME` with your GitHub username and `$GITHUB_TOKEN` with your token.

### Docker Compose (Local Build)

If you prefer to build the Docker image locally:

1. **Clone the repository**:

   ```bash
   git clone https://github.com/cellwebb/discord-plex-announcer.git
   cd discord-plex-announcer
   ```

2. **Configure the bot**:

   ```bash
   cp .env.example .env
   # Edit .env with your Discord and Plex credentials
   ```

3. **Build and run the container**:

   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **View logs**:

   ```bash
   docker-compose logs -f
   ```

### Synology NAS Deployment

For Synology NAS users:

1. **Prerequisites**:

   - Install Docker package from Synology Package Center

2. **Setup using SSH**:

   ```bash
   # Connect to your NAS via SSH
   ssh admin@your-nas-ip

   # Create a directory for the bot
   mkdir -p /volume1/docker/plex-discord-bot
   cd /volume1/docker/plex-discord-bot

   # Create docker-compose.yml
   cat > docker-compose.yml << 'EOF'
   services:
     plex-discord-bot:
       container_name: plex-discord-bot
       image: ghcr.io/cellwebb/discord-plex-announcer:latest
       restart: unless-stopped
       volumes:
         - ./:/app
       environment:
         - DISCORD_TOKEN=${DISCORD_TOKEN}
         - CHANNEL_ID=${CHANNEL_ID}
         - PLEX_URL=${PLEX_URL}
         - PLEX_TOKEN=${PLEX_TOKEN}
         - MOVIE_LIBRARY=${MOVIE_LIBRARY:-Movies}
         - TV_LIBRARY=${TV_LIBRARY:-TV Shows}
         - NOTIFY_MOVIES=${NOTIFY_MOVIES:-true}
         - NOTIFY_TV=${NOTIFY_TV:-true}
         - CHECK_INTERVAL=${CHECK_INTERVAL:-3600}
         - DATA_FILE=${DATA_FILE:-processed_media.json}
         - PLEX_CONNECT_RETRY=${PLEX_CONNECT_RETRY:-3}
         - LOGGING_LEVEL=${LOGGING_LEVEL:-INFO}
       healthcheck:
         test: ["CMD", "python", "-c", "import os, sys; sys.exit(0 if os.path.exists('/app/plex_discord_bot.log') else 1)"]
         interval: 1m
         timeout: 10s
         retries: 3
         start_period: 30s
   EOF

   # Create .env file
   cat > .env << 'EOF'
   DISCORD_TOKEN=your_discord_token
   CHANNEL_ID=your_channel_id
   PLEX_URL=http://your_plex_server:32400
   PLEX_TOKEN=your_plex_token
   EOF

   # Run the container
   docker-compose up -d
   ```

3. **Alternative: Using Synology Docker GUI**:

   - Open Docker in the Synology web interface
   - Go to Registry, search for `ghcr.io/cellwebb/discord-plex-announcer` and download
   - Go to Images, select the image and click Launch
   - Configure the container with environment variables and start it

### Manual Installation

If you prefer not to use Docker:

1. **Clone this repository**:

   ```bash
   git clone https://github.com/cellwebb/discord-plex-announcer.git
   cd discord-plex-announcer
   ```

2. **Set up a virtual environment and install dependencies**:

   ```bash
   # Using the Makefile
   make setup
   source venv/bin/activate

   # Or directly
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure the bot**:

   ```bash
   cp .env.example .env
   # Edit .env with your Discord and Plex credentials
   ```

4. **Run the bot**:

   ```bash
   # Using the Makefile
   make run

   # Or directly
   python plex_discord_bot.py
   ```

## ⚙️ Configuration

Configuration can be done via environment variables or command line arguments:

| Environment Variable | Command Line Argument | Description                                                   |
| -------------------- | --------------------- | ------------------------------------------------------------- |
| `DISCORD_TOKEN`      | `--token`             | Discord bot token                                             |
| `CHANNEL_ID`         | `--channel`           | Discord channel ID for notifications                          |
| `PLEX_URL`           | `--plex-url`          | URL of your Plex server (default: `http://localhost:32400`)   |
| `PLEX_TOKEN`         | `--plex-token`        | Plex authentication token                                     |
| `MOVIE_LIBRARY`      | `--movie-library`     | Name of the Plex movie library (default: Movies)              |
| `TV_LIBRARY`         | `--tv-library`        | Name of the Plex TV show library (default: TV Shows)          |
| `NOTIFY_MOVIES`      | `--notify-movies`     | Enable/disable movie notifications (default: true)            |
| `NOTIFY_TV`          | `--notify-tv`         | Enable/disable TV show notifications (default: true)          |
| `CHECK_INTERVAL`     | `--interval`          | Check interval in seconds (default: 3600 - 1 hour)            |
| `DATA_FILE`          | `--data-file`         | File to store processed media (default: processed_media.json) |
| `PLEX_CONNECT_RETRY` | `--retry`             | Number of Plex connection retries (default: 3)                |
| `LOGGING_LEVEL`      | N/A                   | Logging level (default: INFO)                                 |

## 💬 Commands

The bot supports the following commands:

- `!plex help` - Display help information
- `!plex status` - Show the bot's current status
- `!plex check` - Manually check for new media
- `!plex reset` - Reset the processed media database (use with caution)

## 🛠️ Development

This project includes a Makefile to streamline common development tasks:

```bash
# Show all available commands
make help

# Setup the virtual environment and install dependencies
make setup

# Run tests
make test

# Run linting
make lint

# Format code with black
make format

# Run the bot locally
make run

# Docker commands
make docker-build    # Build the Docker image
make docker-up       # Start the Docker container
make docker-down     # Stop the Docker container
make docker-logs     # View Docker container logs

# GitHub Container Registry commands
make ghcr-pull       # Pull the latest image from GitHub Container Registry
make ghcr-up         # Start the container using the image from GitHub Container Registry
make ghcr-down       # Stop the container
make ghcr-logs       # View container logs

# Clean up
make clean
```

The project also includes pre-commit hooks for code quality. After installing dependencies, set up pre-commit with:

```bash
pre-commit install
```

## 🧪 Testing

The project uses pytest for testing. To run tests:

```bash
python -m pytest
```

To run tests with coverage reports:

```bash
python -m pytest --cov=. --cov-report=term
```

## 📄 License

MIT
