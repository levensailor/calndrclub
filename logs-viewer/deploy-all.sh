#!/bin/bash

# CloudWatch Log Viewer - Complete Deployment Script
# Deploys both S3 static website and EC2 backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 CloudWatch Log Viewer - Complete Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if we're in the right directory
if [[ ! -f "$SCRIPT_DIR/cloudwatch_log_streamer.py" ]]; then
    print_status $RED "❌ Error: cloudwatch_log_streamer.py not found"
    echo "   Make sure you're running this script from the logs-viewer directory"
    exit 1
fi

# Check AWS credentials
print_status $BLUE "🔐 Checking AWS credentials..."
if ! python3 -c "import boto3; boto3.client('sts').get_caller_identity()" 2>/dev/null; then
    print_status $RED "❌ AWS credentials not configured"
    echo "   Please configure your AWS credentials first:"
    echo "   aws configure"
    echo "   or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    exit 1
fi

print_status $GREEN "✅ AWS credentials verified"

# Step 1: Deploy S3 static website
print_status $BLUE "📦 Step 1: Deploying S3 static website..."
cd "$SCRIPT_DIR"
python3 deploy-s3-website.py

if [[ $? -eq 0 ]]; then
    S3_URL="http://calndr-log-viewer-public.s3-website-us-east-1.amazonaws.com"
    print_status $GREEN "✅ S3 website deployed: $S3_URL"
else
    print_status $RED "❌ S3 deployment failed"
    exit 1
fi

# Step 2: Deploy EC2 backend
print_status $BLUE "🖥️  Step 2: Deploying EC2 backend..."
python3 deploy-backend-to-ec2.py

if [[ $? -eq 0 ]]; then
    # Extract EC2 IP from the output
    EC2_IP=$(python3 deploy-backend-to-ec2.py 2>/dev/null | grep "Service URL:" | awk '{print $3}' | sed 's|http://||')
    if [[ -n "$EC2_IP" ]]; then
        print_status $GREEN "✅ EC2 backend deployed: http://$EC2_IP"
    else
        print_status $YELLOW "⚠️  EC2 backend deployed but IP not detected"
    fi
else
    print_status $RED "❌ EC2 deployment failed"
    exit 1
fi

# Step 3: Create updated static files with real backend connection
print_status $BLUE "🔧 Step 3: Creating updated static files..."

# Create a new index.html that connects to the EC2 backend
cat > index-with-backend.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calndr CloudWatch Log Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1419;
            color: #e6e6e6;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: #1a1f2e;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #2d3748;
        }
        
        .header h1 {
            color: #60a5fa;
            margin-bottom: 10px;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ef4444;
        }
        
        .status-indicator.connected {
            background: #10b981;
        }
        
        .controls {
            background: #1a1f2e;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #2d3748;
        }
        
        .control-group {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        
        button:hover {
            background: #2563eb;
        }
        
        button:disabled {
            background: #6b7280;
            cursor: not-allowed;
        }
        
        .log-container {
            background: #1a1f2e;
            border-radius: 8px;
            border: 1px solid #2d3748;
            height: 600px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .log-header {
            background: #2d3748;
            padding: 12px 20px;
            border-bottom: 1px solid #4a5568;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .log-header h3 {
            color: #e2e8f0;
        }
        
        .log-count {
            background: #4b5563;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .log-content {
            flex: 1;
            overflow-y: auto;
            padding: 0;
        }
        
        .log-entry {
            padding: 8px 20px;
            border-bottom: 1px solid #2d3748;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px;
            line-height: 1.4;
        }
        
        .log-entry:hover {
            background: #2d3748;
        }
        
        .log-timestamp {
            color: #9ca3af;
            font-size: 11px;
            margin-right: 10px;
        }
        
        .log-level {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            margin-right: 10px;
            text-transform: uppercase;
        }
        
        .log-level.error {
            background: #dc2626;
            color: white;
        }
        
        .log-level.warning {
            background: #d97706;
            color: white;
        }
        
        .log-level.info {
            background: #059669;
            color: white;
        }
        
        .log-level.debug {
            background: #6366f1;
            color: white;
        }
        
        .log-stream {
            color: #60a5fa;
            font-size: 11px;
            margin-right: 10px;
        }
        
        .log-message {
            color: #e5e7eb;
        }
        
        .error-message {
            background: #dc2626;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .info-message {
            background: #3b82f6;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .connection-info {
            background: #1a1f2e;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #2d3748;
        }
        
        .connection-info h3 {
            color: #e2e8f0;
            margin-bottom: 10px;
        }
        
        .connection-details {
            font-family: monospace;
            font-size: 12px;
            color: #9ca3af;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Calndr CloudWatch Log Viewer</h1>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-indicator" id="connection-status"></div>
                    <span id="connection-text">Disconnected</span>
                </div>
                <div class="status-item">
                    <span>ECS Cluster: calndr-staging-cluster</span>
                </div>
                <div class="status-item">
                    <span>Service: calndr-staging-service</span>
                </div>
                <div class="status-item">
                    <span>Log Group: /ecs/calndr-staging</span>
                </div>
            </div>
        </div>
        
        <div class="connection-info">
            <h3>🔗 Backend Connection</h3>
            <div class="connection-details">
                <div>WebSocket URL: <span id="ws-url">ws://your-ec2-ip/ws</span></div>
                <div>Health Check: <span id="health-url">http://your-ec2-ip/health</span></div>
                <div>Status: <span id="backend-status">Unknown</span></div>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <button id="connect-btn">Connect to Backend</button>
                <button id="disconnect-btn" disabled>Disconnect</button>
                <button id="test-backend-btn">Test Backend</button>
            </div>
        </div>
        
        <div id="messages"></div>
        
        <div class="log-container">
            <div class="log-header">
                <h3>📋 Real-time Logs</h3>
                <div class="log-count" id="log-count">0 logs</div>
            </div>
            <div class="log-content" id="log-content">
                <div class="no-tasks">Connect to backend to start viewing logs</div>
            </div>
        </div>
    </div>

    <script>
        class CloudWatchLogViewer {
            constructor() {
                this.ws = null;
                this.isConnected = false;
                this.logCount = 0;
                this.backendUrl = null;
                this.initializeElements();
                this.bindEvents();
                this.detectBackendUrl();
            }
            
            initializeElements() {
                this.connectBtn = document.getElementById('connect-btn');
                this.disconnectBtn = document.getElementById('disconnect-btn');
                this.testBackendBtn = document.getElementById('test-backend-btn');
                this.connectionStatus = document.getElementById('connection-status');
                this.connectionText = document.getElementById('connection-text');
                this.messagesContainer = document.getElementById('messages');
                this.logContent = document.getElementById('log-content');
                this.logCountElement = document.getElementById('log-count');
                this.wsUrlElement = document.getElementById('ws-url');
                this.healthUrlElement = document.getElementById('health-url');
                this.backendStatusElement = document.getElementById('backend-status');
            }
            
            bindEvents() {
                this.connectBtn.addEventListener('click', () => this.connect());
                this.disconnectBtn.addEventListener('click', () => this.disconnect());
                this.testBackendBtn.addEventListener('click', () => this.testBackend());
            }
            
            detectBackendUrl() {
                // Try to detect EC2 IP from common patterns
                const possibleUrls = [
                    'ws://ec2-3-80-1-2.compute-1.amazonaws.com/ws',
                    'ws://ec2-18-204-8-77.compute-1.amazonaws.com/ws',
                    'ws://ec2-54-157-32-68.compute-1.amazonaws.com/ws'
                ];
                
                // For now, use a placeholder
                this.backendUrl = 'ws://your-ec2-ip/ws';
                this.updateConnectionInfo();
            }
            
            updateConnectionInfo() {
                this.wsUrlElement.textContent = this.backendUrl;
                this.healthUrlElement.textContent = this.backendUrl.replace('ws://', 'http://').replace('/ws', '/health');
            }
            
            async testBackend() {
                const healthUrl = this.backendUrl.replace('ws://', 'http://').replace('/ws', '/health');
                this.backendStatusElement.textContent = 'Testing...';
                
                try {
                    const response = await fetch(healthUrl, { mode: 'no-cors' });
                    this.backendStatusElement.textContent = 'Online';
                    this.showMessage('✅ Backend is online', 'info');
                } catch (error) {
                    this.backendStatusElement.textContent = 'Offline';
                    this.showMessage('❌ Backend is offline', 'error');
                }
            }
            
            connect() {
                if (this.isConnected) return;
                
                if (this.backendUrl === 'ws://your-ec2-ip/ws') {
                    this.showMessage('⚠️ Please update the backend URL with your EC2 IP address', 'error');
                    return;
                }
                
                this.ws = new WebSocket(this.backendUrl);
                
                this.ws.onopen = () => {
                    this.isConnected = true;
                    this.updateConnectionStatus();
                    this.updateButtons();
                    this.showMessage('✅ Connected to CloudWatch logs', 'info');
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'log') {
                            this.addLogEntry(data.data);
                        }
                    } catch (error) {
                        console.error('Error parsing message:', error);
                    }
                };
                
                this.ws.onclose = () => {
                    this.isConnected = false;
                    this.updateConnectionStatus();
                    this.updateButtons();
                    this.showMessage('❌ Disconnected from CloudWatch logs', 'error');
                };
                
                this.ws.onerror = (error) => {
                    this.showMessage('❌ WebSocket connection error', 'error');
                    console.error('WebSocket error:', error);
                };
            }
            
            disconnect() {
                if (this.ws) {
                    this.ws.close();
                }
                this.isConnected = false;
                this.updateConnectionStatus();
                this.updateButtons();
                this.clearLogs();
            }
            
            updateConnectionStatus() {
                if (this.isConnected) {
                    this.connectionStatus.classList.add('connected');
                    this.connectionText.textContent = 'Connected';
                } else {
                    this.connectionStatus.classList.remove('connected');
                    this.connectionText.textContent = 'Disconnected';
                }
            }
            
            updateButtons() {
                this.connectBtn.disabled = this.isConnected;
                this.disconnectBtn.disabled = !this.isConnected;
            }
            
            showMessage(message, type = 'info') {
                const messageDiv = document.createElement('div');
                messageDiv.className = type === 'error' ? 'error-message' : 'info-message';
                messageDiv.textContent = message;
                
                this.messagesContainer.appendChild(messageDiv);
                
                setTimeout(() => {
                    messageDiv.remove();
                }, 5000);
            }
            
            addLogEntry(logData) {
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                
                logEntry.innerHTML = `
                    <span class="log-timestamp">${logData.timestamp}</span>
                    <span class="log-level ${logData.level.toLowerCase()}">${logData.level}</span>
                    <span class="log-stream">${logData.stream}</span>
                    <span class="log-message">${logData.message}</span>
                `;
                
                this.logContent.appendChild(logEntry);
                this.logContent.scrollTop = this.logContent.scrollHeight;
                
                this.logCount++;
                this.logCountElement.textContent = `${this.logCount} logs`;
                
                // Keep only last 100 logs
                while (this.logContent.children.length > 100) {
                    this.logContent.removeChild(this.logContent.firstChild);
                }
            }
            
            clearLogs() {
                this.logContent.innerHTML = '<div class="no-tasks">Connect to backend to start viewing logs</div>';
                this.logCount = 0;
                this.logCountElement.textContent = '0 logs';
            }
        }
        
        // Initialize the log viewer when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new CloudWatchLogViewer();
        });
    </script>
</body>
</html>
EOF

print_status $GREEN "✅ Created updated static files"

# Final summary
print_status $GREEN "\n🎉 Deployment completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Deployment Summary:"
echo ""
echo "🌐 S3 Static Website:"
echo "   URL: $S3_URL"
echo "   Purpose: Demo version with simulated data"
echo ""
echo "🖥️  EC2 Backend:"
echo "   Purpose: Real-time CloudWatch log streaming"
echo "   Status: Deployed and running"
echo ""
echo "📝 Next Steps:"
echo "   1. Get your EC2 instance IP address"
echo "   2. Update the WebSocket URL in index-with-backend.html"
echo "   3. Upload the updated file to S3"
echo "   4. Test the real-time log streaming"
echo ""
echo "🔧 Management Commands:"
echo "   Check EC2 status: aws ec2 describe-instances --filters 'Name=tag:Name,Values=calndr-log-viewer'"
echo "   SSH to EC2: ssh -i ~/.ssh/aws-2024.pem ec2-user@YOUR_EC2_IP"
echo "   View EC2 logs: ssh -i ~/.ssh/aws-2024.pem ec2-user@YOUR_EC2_IP 'sudo journalctl -u calndr-log-viewer -f'" 