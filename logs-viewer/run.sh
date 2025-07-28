#!/bin/bash

# CloudWatch Log Viewer Startup Script
# Simple real-time log viewer for Calndr Staging ECS deployment

set -e

LOG_VIEWER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="CloudWatch Log Viewer"
VENV_DIR="$LOG_VIEWER_DIR/venv"

echo "🚀 Starting $SCRIPT_NAME..."
echo "📁 Working directory: $LOG_VIEWER_DIR"

# Check if we're in the logs-viewer directory
if [[ ! -f "$LOG_VIEWER_DIR/cloudwatch_log_streamer.py" ]]; then
    echo "❌ Error: cloudwatch_log_streamer.py not found"
    echo "   Make sure you're running this script from the logs-viewer directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "📥 Installing/updating dependencies..."
pip install -r requirements.txt

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
if ! python -c "import boto3; boto3.client('logs', region_name='us-east-1').describe_log_groups(limit=1)" 2>/dev/null; then
    echo "⚠️  Warning: AWS credentials may not be configured properly"
    echo "   Make sure your AWS credentials are set up in ~/.aws/credentials"
    echo "   or through environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
    echo ""
    echo "   The service will still start, but may not be able to connect to CloudWatch"
    echo ""
fi

# Check if static directory exists
if [[ ! -d "$LOG_VIEWER_DIR/static" ]]; then
    echo "❌ Error: static directory not found"
    echo "   Make sure the static/index.html file exists"
    exit 1
fi

# Start the service
echo "🌐 Starting CloudWatch Log Viewer on http://localhost:8001"
echo "📊 Monitoring CloudWatch log group: /ecs/calndr-staging"
echo "🔍 Health check filtering: enabled by default"
echo ""
echo "Press Ctrl+C to stop the service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$LOG_VIEWER_DIR"
python cloudwatch_log_streamer.py 