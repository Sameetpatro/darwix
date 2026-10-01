#!/usr/bin/env python3
"""
Entry point launcher for the Darwix AI Voice Agent.
"""
import uvicorn
from app.config import settings
from app.logging_config import logger

if __name__ == "__main__":
    logger.info("Starting Darwix Voice Agent Server (Vani) on http://%s:%d", settings.host, settings.port)
    uvicorn.run(
        "app.server:app",
        host=settings.host,
        port=settings.port,
        reload=(settings.environment == "development"),
        log_level=settings.log_level.lower(),
    )
