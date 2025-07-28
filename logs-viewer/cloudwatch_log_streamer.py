#!/usr/bin/env python3

"""
CloudWatch Log Streamer for ECS Staging Deployment
Real-time log viewer using websockets to make troubleshooting easier
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Set, Optional

import boto3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s EST - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CloudWatch configuration
LOG_GROUP_NAME = "/ecs/calndr-staging"
AWS_REGION = "us-east-1"

class CloudWatchLogStreamer:
    def __init__(self):
        self.cloudwatch_logs = boto3.client('logs', region_name=AWS_REGION)
        self.connected_clients: Set[WebSocket] = set()
        self.is_streaming = False
        self.hide_health_checks = True
        
    async def add_client(self, websocket: WebSocket):
        """Add a new websocket client"""
        self.connected_clients.add(websocket)
        logger.info(f"✅ New client connected. Total clients: {len(self.connected_clients)}")
        
        if not self.is_streaming:
            await self.start_streaming()
    
    async def remove_client(self, websocket: WebSocket):
        """Remove a websocket client"""
        self.connected_clients.discard(websocket)
        logger.info(f"❌ Client disconnected. Total clients: {len(self.connected_clients)}")
        
        if len(self.connected_clients) == 0:
            self.is_streaming = False
            logger.info("🛑 No clients connected, stopping log streaming")
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.connected_clients:
            return
            
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.connected_clients.discard(client)
    
    def should_filter_log(self, log_message: str) -> bool:
        """Check if log should be filtered out"""
        if not self.hide_health_checks:
            return False
            
        # Filter out health check related logs
        health_patterns = [
            'GET /health',
            '"GET /health HTTP/1.1" 200',
            'health check',
            'healthcheck',
            '/health endpoint'
        ]
        
        log_lower = log_message.lower()
        return any(pattern.lower() in log_lower for pattern in health_patterns)
    
    async def get_recent_logs(self) -> list:
        """Get recent logs from CloudWatch"""
        try:
            # Get logs from the last 10 minutes
            end_time = int(time.time() * 1000)
            start_time = end_time - (10 * 60 * 1000)  # 10 minutes ago
            
            response = self.cloudwatch_logs.filter_log_events(
                logGroupName=LOG_GROUP_NAME,
                startTime=start_time,
                endTime=end_time,
                limit=50  # Get last 50 events
            )
            
            events = response.get('events', [])
            # Sort by timestamp (ascending)
            events.sort(key=lambda x: x.get('timestamp', 0))
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Error fetching recent logs: {e}")
            return []
    
    async def get_real_time_logs(self, last_timestamp: Optional[int] = None):
        """Get real-time logs from CloudWatch"""
        try:
            # Get logs from the last minute or from last_timestamp
            end_time = int(time.time() * 1000)
            start_time = last_timestamp + 1 if last_timestamp else end_time - (60 * 1000)
            
            response = self.cloudwatch_logs.filter_log_events(
                logGroupName=LOG_GROUP_NAME,
                startTime=start_time,
                endTime=end_time
            )
            
            return response.get('events', [])
            
        except Exception as e:
            logger.error(f"❌ Error fetching real-time logs: {e}")
            return []
    
    async def start_streaming(self):
        """Start streaming logs to connected clients"""
        if self.is_streaming:
            return
            
        self.is_streaming = True
        logger.info("🚀 Starting CloudWatch log streaming...")
        
        # Send initial recent logs
        await self.send_recent_logs()
        
        # Start real-time streaming
        last_timestamp = int(time.time() * 1000)
        
        while self.is_streaming and self.connected_clients:
            try:
                # Get new logs
                events = await self.get_real_time_logs(last_timestamp)
                
                for event in events:
                    if not self.should_filter_log(event.get('message', '')):
                        formatted_log = self.format_log_event(event)
                        await self.broadcast_message({
                            'type': 'log',
                            'data': formatted_log
                        })
                    
                    # Update last timestamp
                    last_timestamp = max(last_timestamp, event.get('timestamp', last_timestamp))
                
                # Wait before next poll
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in streaming loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def send_recent_logs(self):
        """Send recent logs to newly connected clients"""
        logger.info("📋 Sending recent logs to new client...")
        
        events = await self.get_recent_logs()
        
        for event in events:
            if not self.should_filter_log(event.get('message', '')):
                formatted_log = self.format_log_event(event)
                await self.broadcast_message({
                    'type': 'log',
                    'data': formatted_log
                })
    
    def format_log_event(self, event: dict) -> dict:
        """Format CloudWatch log event for display"""
        timestamp = event.get('timestamp', 0)
        message = event.get('message', '').strip()
        log_stream = event.get('logStreamName', 'unknown')
        
        # Format timestamp to EST
        dt = datetime.fromtimestamp(timestamp / 1000)
        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S EST')
        
        # Determine log level
        log_level = 'INFO'
        if any(level in message.upper() for level in ['ERROR', 'EXCEPTION', '❌']):
            log_level = 'ERROR'
        elif any(level in message.upper() for level in ['WARN', '⚠️']):
            log_level = 'WARNING'
        elif any(level in message.upper() for level in ['DEBUG', '🔍']):
            log_level = 'DEBUG'
        
        return {
            'timestamp': formatted_time,
            'level': log_level,
            'stream': log_stream,
            'message': message,
            'raw_timestamp': timestamp
        }
    
    async def toggle_health_filter(self, hide_health: bool):
        """Toggle health check filtering"""
        self.hide_health_checks = hide_health
        status = "enabled" if hide_health else "disabled"
        logger.info(f"🔧 Health check filtering {status}")
        
        await self.broadcast_message({
            'type': 'filter_status',
            'data': {
                'hide_health_checks': hide_health,
                'message': f"Health check filtering {status}"
            }
        })

# Initialize the streamer
log_streamer = CloudWatchLogStreamer()

# FastAPI app
app = FastAPI(title="CloudWatch Log Viewer", version="1.0.0")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    """Serve the main log viewer page"""
    return FileResponse('static/index.html')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for log streaming"""
    await websocket.accept()
    await log_streamer.add_client(websocket)
    
    try:
        while True:
            # Listen for client messages (e.g., filter toggles)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'toggle_health_filter':
                hide_health = message.get('hide_health', True)
                await log_streamer.toggle_health_filter(hide_health)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        await log_streamer.remove_client(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "clients_connected": len(log_streamer.connected_clients),
        "streaming": log_streamer.is_streaming,
        "log_group": LOG_GROUP_NAME,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("🚀 Starting CloudWatch Log Viewer...")
    logger.info(f"📊 Monitoring log group: {LOG_GROUP_NAME}")
    logger.info(f"🌎 Region: {AWS_REGION}")
    
    uvicorn.run(
        "cloudwatch_log_streamer:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    ) 