#!/bin/bash

# CloudWatch Log Viewer Service Installer
# Installs the log viewer as a systemd service for persistent operation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="cloudwatch-log-viewer"
SERVICE_FILE="$SCRIPT_DIR/cloudwatch-log-viewer.service"
SYSTEMD_DIR="$HOME/Library/LaunchAgents"

echo "🚀 Installing CloudWatch Log Viewer as a system service..."
echo "📁 Script directory: $SCRIPT_DIR"

# Check if we're in the logs-viewer directory
if [[ ! -f "$SCRIPT_DIR/cloudwatch_log_streamer.py" ]]; then
    echo "❌ Error: cloudwatch_log_streamer.py not found"
    echo "   Make sure you're running this script from the logs-viewer directory"
    exit 1
fi

# Check if service file exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "❌ Error: cloudwatch-log-viewer.service not found"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Set up virtual environment
echo "📦 Setting up virtual environment..."
if [[ ! -d "$SCRIPT_DIR/venv" ]]; then
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment and install dependencies
source "$SCRIPT_DIR/venv/bin/activate"
pip install -r "$SCRIPT_DIR/requirements.txt"

# Create launchd plist file for macOS
echo "🔧 Creating launchd service configuration..."
cat > "$SYSTEMD_DIR/com.levensailor.cloudwatch-log-viewer.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.levensailor.cloudwatch-log-viewer</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/venv/bin/python</string>
        <string>$SCRIPT_DIR/cloudwatch_log_streamer.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/service.log</string>
    
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/service-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$SCRIPT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

# Set proper permissions
chmod 644 "$SYSTEMD_DIR/com.levensailor.cloudwatch-log-viewer.plist"

# Load the service
echo "🔄 Loading the service..."
launchctl load "$SYSTEMD_DIR/com.levensailor.cloudwatch-log-viewer.plist"

# Start the service
echo "🚀 Starting the service..."
launchctl start com.levensailor.cloudwatch-log-viewer

# Check if service is running
sleep 3
if launchctl list | grep -q "com.levensailor.cloudwatch-log-viewer"; then
    echo "✅ Service installed and started successfully!"
    echo ""
    echo "📊 Service Information:"
    echo "   Service Name: com.levensailor.cloudwatch-log-viewer"
    echo "   Web Interface: http://localhost:8001"
    echo "   Log Files: $SCRIPT_DIR/logs/"
    echo "   Config File: $SYSTEMD_DIR/com.levensailor.cloudwatch-log-viewer.plist"
    echo ""
    echo "🔧 Management Commands:"
    echo "   Start:   launchctl start com.levensailor.cloudwatch-log-viewer"
    echo "   Stop:    launchctl stop com.levensailor.cloudwatch-log-viewer"
    echo "   Restart: launchctl unload $SYSTEMD_DIR/com.levensailor.cloudwatch-log-viewer.plist && launchctl load $SYSTEMD_DIR/com.levensailor.cloudwatch-log-viewer.plist"
    echo "   Status:  launchctl list | grep cloudwatch-log-viewer"
    echo "   Logs:    tail -f $SCRIPT_DIR/logs/service.log"
    echo ""
    echo "🔄 The service will automatically start on system boot"
else
    echo "❌ Failed to start the service"
    echo "   Check the logs at: $SCRIPT_DIR/logs/service-error.log"
    exit 1
fi 