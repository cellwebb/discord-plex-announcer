"""
Webhook server to receive Plex notifications.
"""

import json
import logging

from aiohttp import web

from plex_announcer.core.discord_bot import PlexDiscordBot

logger = logging.getLogger(__name__)


class PlexWebhookServer:
    """Server to receive Plex webhooks and forward to the Discord bot."""

    def __init__(
        self,
        discord_bot: PlexDiscordBot,
        host: str = "0.0.0.0",
        port: int = 10000,
    ):
        """Initialize the webhook server.

        Args:
            discord_bot: The Discord bot instance to forward notifications to
            host: Host to bind the server to
            port: Port to bind the server to
        """
        self.discord_bot = discord_bot
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.add_routes([web.post("/webhook", self.handle_webhook)])
        self.runner = None
        self.site = None

    async def start(self) -> None:
        """Start the webhook server."""
        logger.info(f"Starting Plex webhook server on {self.host}:{self.port}")
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info("Webhook server started successfully")

    async def stop(self) -> None:
        """Stop the webhook server."""
        if self.site:
            logger.info("Shutting down webhook server")
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Webhook server stopped")

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook from Plex."""
        try:
            # Plex webhooks come as multipart/form-data with a 'payload' field
            data = await request.post()

            if "payload" not in data:
                logger.warning("Received webhook without payload")
                return web.Response(text="No payload found", status=400)

            payload = json.loads(data["payload"])
            logger.debug(f"Received webhook: {payload}")

            # Process the payload based on event type
            event_type = payload.get("event")
            if not event_type:
                return web.Response(text="No event type in payload", status=400)

            # Handle different event types
            if event_type == "library.new":
                # New item added to library
                await self._handle_new_media(payload)
            elif event_type == "media.play":
                # Media playback started
                logger.info(f"Media playback started: {payload.get('Metadata', {}).get('title')}")
            # Add more event handlers as needed

            return web.Response(text="Webhook received", status=200)

        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return web.Response(text="Error processing webhook", status=500)

    async def _handle_new_media(self, payload: dict) -> None:
        """Handle new media added to library."""
        try:
            metadata = payload.get("Metadata", {})
            media_type = metadata.get("type")

            if media_type == "movie":
                # New movie added
                await self.discord_bot.announce_new_movie_from_webhook(metadata)
            elif media_type == "episode":
                # New episode added
                await self.discord_bot.announce_new_episode_from_webhook(metadata)
            elif media_type == "show":
                # New show added
                await self.discord_bot.announce_new_show_from_webhook(metadata)
        except Exception as e:
            logger.error(f"Error handling new media webhook: {e}", exc_info=True)
