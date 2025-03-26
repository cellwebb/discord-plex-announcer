#!/usr/bin/env python3
"""
Simple standalone webhook server for testing Plex webhooks.
"""

import asyncio
import json
import logging

from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("webhook-test")


class SimpleWebhookServer:
    def __init__(self, host="0.0.0.0", port=10000):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.add_routes(
            [web.get("/test", self.test_endpoint), web.post("/webhook", self.handle_webhook)]
        )
        self.runner = None
        self.site = None

    async def start(self):
        """Start the webhook server."""
        try:
            logger.info(f"Starting webhook server on {self.host}:{self.port}")
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            logger.info(f"Webhook server started successfully on {self.host}:{self.port}")
            logger.info(f"Test endpoint available at http://{self.host}:{self.port}/test")
            logger.info(f"Webhook endpoint available at http://{self.host}:{self.port}/webhook")
        except Exception as e:
            logger.error(f"Failed to start webhook server: {e}", exc_info=True)
            if hasattr(self, "runner") and self.runner:
                await self.runner.cleanup()

    async def stop(self):
        """Stop the webhook server."""
        if self.runner:
            logger.info("Stopping webhook server")
            await self.runner.cleanup()
            logger.info("Webhook server stopped")

    async def test_endpoint(self, request):
        """Test endpoint to verify the webhook server is running."""
        logger.info("Test endpoint accessed")
        return web.Response(text="Webhook server is running")

    async def handle_webhook(self, request):
        """Handle a webhook request from Plex."""
        try:
            logger.info(f"Received webhook request from {request.remote}")

            # Get the form data
            data = await request.post()

            # Log the raw request data
            logger.info(f"Raw request data: {data}")

            # Extract the payload
            if "payload" in data:
                payload = json.loads(data["payload"])
                logger.info(f"Webhook payload: {json.dumps(payload, indent=2)}")

                # Extract event type and metadata
                event_type = payload.get("event")
                logger.info(f"Event type: {event_type}")

                if "Metadata" in payload:
                    metadata = payload["Metadata"]
                    logger.info(f"Metadata: {json.dumps(metadata, indent=2)}")
            else:
                logger.warning("No payload found in webhook request")

            return web.Response(text="Webhook received")
        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return web.Response(text="Error processing webhook", status=500)


async def main():
    server = SimpleWebhookServer()
    await server.start()

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
