FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY plex_announcer/ /app/plex_announcer/
COPY *.py *.json .env* ./

# Create non-root user and switch to it for security
RUN useradd -m discordbot && \
    chown -R discordbot:discordbot /app

USER discordbot

# Make scripts executable
RUN chmod +x run.py healthcheck.py

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python healthcheck.py || exit 1

# Add proper signal handling
CMD ["python", "run.py"]
