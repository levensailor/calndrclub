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
from typing import Set, Optional, Dict, List

import boto3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s EST - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CloudWatch and ECS configuration
LOG_GROUP_NAME = "/ecs/calndr-staging"
AWS_REGION = "us-east-1"
ECS_CLUSTER_NAME = "calndr-staging-cluster"
ECS_SERVICE_NAME = "calndr-staging-service"

class ECSTaskManager:
    def __init__(self):
        self.ecs_client = boto3.client('ecs', region_name=AWS_REGION)
        self.logs_client = boto3.client('logs', region_name=AWS_REGION)
        
    async def get_running_tasks(self) -> List[Dict]:
        """Get currently running tasks for the service"""
        try:
            # Get tasks for the service
            response = self.ecs_client.list_tasks(
                cluster=ECS_CLUSTER_NAME,
                serviceName=ECS_SERVICE_NAME,
                desiredStatus='RUNNING'
            )
            
            task_arns = response.get('taskArns', [])
            if not task_arns:
                return []
            
            # Get task details
            tasks_response = self.ecs_client.describe_tasks(
                cluster=ECS_CLUSTER_NAME,
                tasks=task_arns
            )
            
            tasks_info = []
            for task in tasks_response.get('tasks', []):
                task_info = {
                    'taskArn': task.get('taskArn', ''),
                    'taskId': task.get('taskArn', '').split('/')[-1] if task.get('taskArn') else 'unknown',
                    'taskDefinitionArn': task.get('taskDefinitionArn', ''),
                    'taskDefinition': task.get('taskDefinitionArn', '').split('/')[-1] if task.get('taskDefinitionArn') else 'unknown',
                    'lastStatus': task.get('lastStatus', 'unknown'),
                    'healthStatus': task.get('healthStatus', 'unknown'),
                    'createdAt': task.get('createdAt').isoformat() if task.get('createdAt') else 'unknown',
                    'startedAt': task.get('startedAt').isoformat() if task.get('startedAt') else 'unknown',
                    'containers': []
                }
                
                # Get container information
                for container in task.get('containers', []):
                    container_info = {
                        'name': container.get('name', 'unknown'),
                        'lastStatus': container.get('lastStatus', 'unknown'),
                        'healthStatus': container.get('healthStatus', 'unknown'),
                        'networkBindings': container.get('networkBindings', [])
                    }
                    task_info['containers'].append(container_info)
                
                tasks_info.append(task_info)
            
            return tasks_info
            
        except Exception as e:
            logger.error(f"❌ Error getting running tasks: {e}")
            return []
    
    async def restart_service(self) -> Dict:
        """Restart the ECS service by forcing a new deployment"""
        try:
            logger.info(f"🔄 Restarting ECS service: {ECS_SERVICE_NAME}")
            
            response = self.ecs_client.update_service(
                cluster=ECS_CLUSTER_NAME,
                service=ECS_SERVICE_NAME,
                forceNewDeployment=True
            )
            
            deployment_id = None
            for deployment in response.get('service', {}).get('deployments', []):
                if deployment.get('status') == 'PRIMARY':
                    deployment_id = deployment.get('id')
                    break
            
            logger.info(f"✅ Service restart initiated. Deployment ID: {deployment_id}")
            
            return {
                'success': True,
                'message': f'Service restart initiated successfully',
                'deploymentId': deployment_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error restarting service: {e}")
            return {
                'success': False,
                'message': f'Error restarting service: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

class CloudWatchLogStreamer:
    def __init__(self):
        self.cloudwatch_logs = boto3.client('logs', region_name=AWS_REGION)
        self.ecs_manager = ECSTaskManager()
        self.connected_clients: Set[WebSocket] = set()
        self.is_streaming = False
        self.hide_health_checks = True
        
    async def add_client(self, websocket: WebSocket):
        """Add a new websocket client"""
        self.connected_clients.add(websocket)
        logger.info(f"✅ New client connected. Total clients: {len(self.connected_clients)}")
        
        # Send current ECS status to new client
        await self.send_ecs_status(websocket)
        
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
    
    async def send_ecs_status(self, websocket: WebSocket = None):
        """Send ECS status to client(s)"""
        try:
            tasks = await self.ecs_manager.get_running_tasks()
            
            ecs_status = {
                'type': 'ecs_status',
                'data': {
                    'cluster': ECS_CLUSTER_NAME,
                    'service': ECS_SERVICE_NAME,
                    'tasks': tasks,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            if websocket:
                await websocket.send_text(json.dumps(ecs_status))
            else:
                await self.broadcast_message(ecs_status)
                
        except Exception as e:
            logger.error(f"❌ Error sending ECS status: {e}")
    
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
        ecs_status_counter = 0
        
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
                
                # Update ECS status every 30 seconds (15 cycles)
                ecs_status_counter += 1
                if ecs_status_counter >= 15:
                    await self.send_ecs_status()
                    ecs_status_counter = 0
                
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

@app.get("/api/ecs/tasks")
async def get_ecs_tasks():
    """Get current ECS task information"""
    try:
        tasks = await log_streamer.ecs_manager.get_running_tasks()
        return {
            'success': True,
            'cluster': ECS_CLUSTER_NAME,
            'service': ECS_SERVICE_NAME,
            'tasks': tasks,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error getting ECS tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ecs/restart")
async def restart_ecs_service():
    """Restart the ECS service"""
    try:
        result = await log_streamer.ecs_manager.restart_service()
        
        # Broadcast restart notification to all connected clients
        await log_streamer.broadcast_message({
            'type': 'service_restart',
            'data': result
        })
        
        return result
    except Exception as e:
        logger.error(f"❌ Error restarting ECS service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            elif message.get('type') == 'request_ecs_status':
                await log_streamer.send_ecs_status(websocket)
            
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
        "cluster": ECS_CLUSTER_NAME,
        "service": ECS_SERVICE_NAME,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("🚀 Starting CloudWatch Log Viewer...")
    logger.info(f"📊 Monitoring log group: {LOG_GROUP_NAME}")
    logger.info(f"🌎 Region: {AWS_REGION}")
    logger.info(f"🎯 ECS Cluster: {ECS_CLUSTER_NAME}")
    logger.info(f"⚙️ ECS Service: {ECS_SERVICE_NAME}")
    
    uvicorn.run(
        "cloudwatch_log_streamer:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    ) 