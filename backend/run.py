#!/usr/bin/env python3
"""
Startup script for the Calndr API.
"""

# Initialize logging first, before importing other modules
from core.logging import setup_logging
logger = setup_logging()

import uvicorn
import requests
import json
from main import app

if __name__ == "__main__":
    logger.info("Starting Calndr API server...")
    url = "https://api.ciscospark.com/v1/messages"

    payload = json.dumps({
    "toPersonEmail": "jlevensailor@presidio.com",
    "text": "calndr backend is running"
    })
    headers = {
    'Authorization': 'Bearer NTYyZTE2OTUtYTc4Ni00MTY3LWFlYjMtMTIwNmFkNzcxYjJiMjhiZDgxMmUtYjIx',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

