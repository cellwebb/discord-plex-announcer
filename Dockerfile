FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY *.py *.json .env* /app/

# Create non-root user and switch to it for security
RUN useradd -m discordbot && \
    chown -R discordbot:discordbot /app

USER discordbot

# Add proper signal handling
CMD ["python", "plex_discord_bot.py"]
