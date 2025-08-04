#!/usr/bin/env python3
"""
Startup script for the Calndr API.
"""

# Initialize logging first, before importing other modules
from core.logging import setup_logging
logger = setup_logging()

import uvicorn
from main import app

if __name__ == "__main__":
    logger.info("Starting Calndr API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
