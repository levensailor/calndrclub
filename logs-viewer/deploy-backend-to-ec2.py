#!/usr/bin/env python3

"""
Deploy CloudWatch Log Viewer Backend to EC2
Creates an EC2 instance with the log viewer backend running
"""

import boto3
import json
import time
import os
import sys
from datetime import datetime

# Configuration
INSTANCE_NAME = "calndr-log-viewer"
INSTANCE_TYPE = "t2.micro"  # Free tier eligible
KEY_NAME = "aws-2024"
SECURITY_GROUP_NAME = "calndr-log-viewer-sg"
REGION = "us-east-1"
AMI_ID = "ami-0c02fb55956c7d316"  # Amazon Linux 2023 AMI for us-east-1

def create_security_group():
    """Create security group for the log viewer"""
    ec2 = boto3.client('ec2', region_name=REGION)
    
    try:
        # Check if security group already exists
        response = ec2.describe_security_groups(
            GroupNames=[SECURITY_GROUP_NAME]
        )
        print(f"✅ Security group {SECURITY_GROUP_NAME} already exists")
        return SECURITY_GROUP_NAME
    except:
        pass
    
    try:
        # Create security group
        response = ec2.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description='Security group for Calndr Log Viewer'
        )
        security_group_id = response['GroupId']
        
        # Add rules
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 8001,
                    'ToPort': 8001,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        
        print(f"✅ Created security group: {SECURITY_GROUP_NAME}")
        return SECURITY_GROUP_NAME
        
    except Exception as e:
        print(f"❌ Error creating security group: {e}")
        return None

def create_ec2_instance():
    """Create EC2 instance for the log viewer"""
    ec2 = boto3.client('ec2', region_name=REGION)
    
    # Check if instance already exists
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [INSTANCE_NAME]},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'pending']}
            ]
        )
        
        if response['Reservations']:
            instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
            print(f"✅ Instance {INSTANCE_NAME} already exists (ID: {instance_id}, State: {state})")
            
            if state == 'stopped':
                print("🔄 Starting existing instance...")
                ec2.start_instances(InstanceIds=[instance_id])
                return instance_id
            elif state == 'running':
                return instance_id
            else:
                print("⏳ Instance is starting, please wait...")
                return instance_id
    except Exception as e:
        print(f"⚠️ Error checking existing instance: {e}")
    
    # Create user data script
    user_data = """#!/bin/bash
# Update system
yum update -y

# Install Python 3 and pip
yum install -y python3 python3-pip git

# Install nginx
yum install -y nginx

# Start and enable nginx
systemctl start nginx
systemctl enable nginx

# Create application directory
mkdir -p /opt/calndr-log-viewer
cd /opt/calndr-log-viewer

# Clone the repository (you'll need to provide the actual repo URL)
# git clone https://github.com/your-repo/calndr-backend-refactor.git .

# For now, we'll create the files manually
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
boto3==1.34.0
python-dotenv==1.0.0
EOF

# Create the log viewer application
cat > cloudwatch_log_streamer.py << 'EOF'
#!/usr/bin/env python3

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

class CloudWatchLogStreamer:
    def __init__(self):
        self.cloudwatch_logs = boto3.client('logs', region_name=AWS_REGION)
        self.connected_clients: Set[WebSocket] = set()
        self.is_streaming = False
        
    async def add_client(self, websocket: WebSocket):
        self.connected_clients.add(websocket)
        logger.info(f"✅ New client connected. Total clients: {len(self.connected_clients)}")
        
        if not self.is_streaming:
            await self.start_streaming()
    
    async def remove_client(self, websocket: WebSocket):
        self.connected_clients.discard(websocket)
        logger.info(f"❌ Client disconnected. Total clients: {len(self.connected_clients)}")
        
        if len(self.connected_clients) == 0:
            self.is_streaming = False
            logger.info("🛑 No clients connected, stopping log streaming")
    
    async def broadcast_message(self, message: dict):
        if not self.connected_clients:
            return
            
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected_clients.add(client)
        
        for client in disconnected_clients:
            self.connected_clients.discard(client)
    
    async def get_recent_logs(self) -> list:
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (10 * 60 * 1000)  # 10 minutes ago
            
            response = self.cloudwatch_logs.filter_log_events(
                logGroupName=LOG_GROUP_NAME,
                startTime=start_time,
                endTime=end_time,
                limit=50
            )
            events = response.get('events', [])
            events.sort(key=lambda x: x.get('timestamp', 0))
            return events
            
        except Exception as e:
            logger.error(f"❌ Error fetching recent logs: {e}")
            return []
    
    async def get_real_time_logs(self, last_timestamp: Optional[int] = None):
        try:
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
                events = await self.get_real_time_logs(last_timestamp)
                
                for event in events:
                    formatted_log = self.format_log_event(event)
                    await self.broadcast_message({
                        'type': 'log',
                        'data': formatted_log
                    })
                    last_timestamp = max(last_timestamp, event.get('timestamp', last_timestamp))
                
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in streaming loop: {e}")
                await asyncio.sleep(5)
    
    async def send_recent_logs(self):
        logger.info("📋 Sending recent logs to new client...")
        events = await self.get_recent_logs()
        
        for event in events:
            formatted_log = self.format_log_event(event)
            await self.broadcast_message({
                'type': 'log',
                'data': formatted_log
            })
    
    def format_log_event(self, event: dict) -> dict:
        timestamp = event.get('timestamp', 0)
        message = event.get('message', '').strip()
        log_stream = event.get('logStreamName', 'unknown')
        
        dt = datetime.fromtimestamp(timestamp / 1000)
        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S EST')
        
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

# Initialize the streamer
log_streamer = CloudWatchLogStreamer()

# FastAPI app
app = FastAPI(title="CloudWatch Log Viewer", version="1.0.0")

@app.get("/")
async def get_index():
    return {"message": "CloudWatch Log Viewer API", "status": "running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await log_streamer.add_client(websocket)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await log_streamer.remove_client(websocket)

@app.get("/health")
async def health_check():
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
EOF

# Install Python dependencies
pip3 install -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/calndr-log-viewer.service << 'EOF'
[Unit]
Description=Calndr CloudWatch Log Viewer
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/calndr-log-viewer
ExecStart=/usr/bin/python3 cloudwatch_log_streamer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable calndr-log-viewer
systemctl start calndr-log-viewer

# Configure nginx as reverse proxy
cat > /etc/nginx/conf.d/calndr-log-viewer.conf << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Restart nginx
systemctl restart nginx

echo "✅ CloudWatch Log Viewer setup completed!"
"""

    try:
        # Create instance
        response = ec2.run_instances(
            ImageId=AMI_ID,
            MinCount=1,
            MaxCount=1,
            InstanceType=INSTANCE_TYPE,
            KeyName=KEY_NAME,
            SecurityGroups=[SECURITY_GROUP_NAME],
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': INSTANCE_NAME},
                        {'Key': 'Purpose', 'Value': 'CloudWatch Log Viewer'},
                        {'Key': 'Environment', 'Value': 'Production'}
                    ]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"✅ Created EC2 instance: {instance_id}")
        
        # Wait for instance to be running
        print("⏳ Waiting for instance to start...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Get public IP
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        print(f"✅ Instance is running with public IP: {public_ip}")
        return instance_id, public_ip
        
    except Exception as e:
        print(f"❌ Error creating EC2 instance: {e}")
        return None, None

def wait_for_service(public_ip, timeout=300):
    """Wait for the service to be available"""
    import requests
    
    print(f"⏳ Waiting for service to be available at http://{public_ip}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{public_ip}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Service is available!")
                return True
        except:
            pass
        
        print("⏳ Service not ready yet, waiting...")
        time.sleep(10)
    
    print("❌ Service did not become available within timeout")
    return False

def main():
    print("🚀 Deploying CloudWatch Log Viewer Backend to EC2")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Create security group
    security_group = create_security_group()
    if not security_group:
        sys.exit(1)
    
    # Create EC2 instance
    instance_id, public_ip = create_ec2_instance()
    if not instance_id or not public_ip:
        sys.exit(1)
    
    # Wait for service to be available
    if wait_for_service(public_ip):
        print("\n✅ Deployment completed successfully!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🌐 Service URL: http://{public_ip}")
        print(f"🔍 Health Check: http://{public_ip}/health")
        print(f"📊 WebSocket: ws://{public_ip}/ws")
        print(f"🖥️  Instance ID: {instance_id}")
        print(f"🔑 SSH Command: ssh -i ~/.ssh/aws-2024.pem ec2-user@{public_ip}")
        print("\n📝 Next Steps:")
        print("   1. Update the static S3 website to connect to this backend")
        print("   2. Test the WebSocket connection")
        print("   3. Monitor the logs for any issues")
    else:
        print("\n❌ Deployment completed but service is not responding")
        print(f"🔑 SSH into the instance to debug: ssh -i ~/.ssh/aws-2024.pem ec2-user@{public_ip}")

if __name__ == "__main__":
    main() 