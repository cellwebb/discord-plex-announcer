# Discord Plex Announcer

A Discord bot that announces when new movies are added to your Plex server.

## Features

- Monitors your Plex server for newly added movies
- Posts announcements to a designated Discord channel
- Includes movie details such as title, summary, year, rating, and genres
- Admin commands to check status and trigger manual checks

## Setup

### Prerequisites

- Python 3.8 or higher
- A Plex server with an authentication token
- A Discord bot token

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/discord-plex-announcer.git
   cd discord-plex-announcer
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on the `.env.example` template:

   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your Discord bot token, channel ID, and Plex server details.

### Getting Your Plex Token

To get your Plex token, you can:

1. Log into Plex web app
2. Open your browser's developer tools and look at the network tab
3. Find a request to your Plex server and look for the `X-Plex-Token` parameter in the URL

### Testing Connections

Before running the bot, you can verify your Discord and Plex connections with the testing script:

```bash
python test_connection.py
```

This will check if:

- Your Discord token is valid
- The specified Discord channel is accessible
- Your Plex server is reachable
- The Movies library exists and can be queried

If any issues are detected, the script will provide guidance on how to fix them.

### Running the Bot

```bash
python main.py
```

Consider using a process manager like `systemd`, `supervisor`, or `pm2` to keep the bot running.

## Usage

The bot automatically checks for new movies at regular intervals (default: every 5 minutes).

### Commands

- `!status` - Shows the current status of the bot and Plex connection
- `!check_now` - Manually triggers a check for new movies (admin only)

## License

See the [LICENSE](LICENSE) file for details.
