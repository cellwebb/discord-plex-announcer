#!/bin/bash
# Simple startup script that won't hang the container

echo "Starting Plex Discord Announcer bot..."
# Run the bot in the background and redirect output to a log file
python run.py > /app/logs/bot.log 2>&1 &

# Write the PID to a file
echo $! > /app/data/bot.pid

# Wait a moment to allow the bot to initialize
sleep 2

echo "Bot started in background. Check logs for details."
echo "Container will now stay running..."

# Keep container running
tail -f /dev/null
