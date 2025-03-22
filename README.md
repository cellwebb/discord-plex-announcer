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
     curl -L https://github.com/cellwebb/discord-plex-announcer/archive/refs/heads/main.zip -o main.zip
     unzip main.zip
     mv discord-plex-announcer-main/* .
     rm -rf discord-plex-announcer-main main.zip
     ```

   - Copy and edit the environment file: `cp .env.example .env`
   - Edit the .env file with your values: `vi .env`

3. **Build and Deploy Options**:

   **Option 1: Build directly on Synology**

   - If your Synology has enough resources, you can build the Docker image directly:

     ```bash
     docker-compose build
     docker-compose up -d
     ```

   **Option 2: Use Docker Container Manager UI**

   - Open Docker Container Manager in DSM
   - Go to "Image" → "Add" → "Add From URL" → Enter the GitHub repository URL
   - Alternatively, use "Container" → "Create" → "Import from docker-compose.yml" and browse to the docker-compose.yml file in your created directory

   **Option 3: Build locally and transfer to Synology**

   - On your local machine, build the image:

     ```bash
     make docker-build
     ```

   - Save the image:

     ```bash
     docker save plex-discord-bot:latest > plex-discord-bot.tar
     ```

   - Transfer to Synology and load:

     ```bash
     scp plex-discord-bot.tar username@synology_ip:/volume1/docker/
     ssh username@synology_ip
     cd /volume1/docker
     docker load < plex-discord-bot.tar
     cd plex-discord-bot
     docker-compose up -d
     ```

4. **Volume Mapping**

   - Map `/volume1/docker/plex-discord-bot` to `/app` inside the container to persist data

5. **Environment Variables**

   - Ensure all required environment variables from the .env file are added to the container configuration

For troubleshooting, check the container logs through the Docker Container Manager interface or run:

```bash
docker-compose logs -f
```

### Deploying with Pre-built Images from GitHub Container Registry

For the simplest deployment experience, you can use our pre-built Docker images from GitHub Container Registry:

1. **On your Synology NAS or any Docker host**:

   - Create a directory for the bot:

     ```bash
     mkdir -p /volume1/docker/plex-discord-bot
     cd /volume1/docker/plex-discord-bot
     ```

   - Create a deployment docker-compose.yml file:

     ```bash
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
     ```

   - Create a .env file with your configuration:

     ```bash
     cat > .env << 'EOF'
     DISCORD_TOKEN=your_discord_token
     CHANNEL_ID=your_channel_id
     PLEX_URL=http://your_plex_server:32400
     PLEX_TOKEN=your_plex_token
     EOF
     ```

   - Run the container:

     ```bash
     docker-compose up -d
     ```

2. **To update to the latest version**:

   ```bash
   docker-compose pull
   docker-compose up -d
   ```

This method pulls the pre-built image directly from GitHub Container Registry, eliminating the need to build the image locally. The images are automatically built and pushed whenever changes are made to the main branch.

### GitHub Container Registry Authentication

If you encounter authentication issues when pulling the image, you may need to authenticate with GitHub Container Registry:

1. Create a GitHub Personal Access Token with the `read:packages` scope at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)

2. Log in to the GitHub Container Registry:

   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```

   Replace `USERNAME` with your GitHub username and `$GITHUB_TOKEN` with your personal access token.

3. Once authenticated, you can pull the image:

   ```bash
   docker pull ghcr.io/cellwebb/discord-plex-announcer:latest
   ```

For most users, authentication may not be necessary as the container images are public. However, GitHub may impose rate limits on anonymous pulls, so authentication is recommended for frequent usage.

### Using docker-compose.deploy.yml

The repository includes a `docker-compose.deploy.yml` file specifically for deploying with the pre-built image from GitHub Container Registry. You can use this file directly:

1. Clone the repository or download just the `docker-compose.deploy.yml` file:

   ```bash
   curl -O https://raw.githubusercontent.com/cellwebb/discord-plex-announcer/main/docker-compose.deploy.yml
   ```

2. Create a `.env` file with your configuration:

   ```bash
   cat > .env << 'EOF'
   DISCORD_TOKEN=your_discord_token
   CHANNEL_ID=your_channel_id
   PLEX_URL=http://your_plex_server:32400
   PLEX_TOKEN=your_plex_token
   EOF
   ```

3. Deploy using the file:

   ```bash
   docker-compose -f docker-compose.deploy.yml up -d
   ```

4. To update to the latest version:

   ```bash
   docker-compose -f docker-compose.deploy.yml pull
   docker-compose -f docker-compose.deploy.yml up -d
   ```

This method is particularly useful if you want to customize the deployment configuration while still using the pre-built image.

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
