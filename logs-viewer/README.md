# CloudWatch Log Viewer

A simple real-time log viewer for the Calndr Staging ECS deployment. This tool provides a web-based interface to stream CloudWatch logs via websockets, making troubleshooting much easier than navigating through the AWS console.

## Features

- 🔴 **Real-time log streaming** from CloudWatch via websockets
- 🚫 **Health check filtering** - toggle to hide/show GET /health events  
- 🎨 **Clean terminal-style interface** with color-coded log levels
- 🔄 **Auto-reconnection** if the connection is lost
- 📜 **Recent logs** displayed when connecting
- 🧹 **Clear logs** button to reset the view
- 📱 **Auto-scroll** with manual scroll detection

## Quick Start

1. **Ensure AWS credentials are configured:**
   ```bash
   # Check if credentials are working
   aws logs describe-log-groups --region us-east-1 --limit 1
   ```

2. **Start the log viewer:**
   ```bash
   cd logs-viewer
   chmod +x run.sh
   ./run.sh
   ```

3. **Open your browser:**
   ```
   http://localhost:8001
   ```

## Configuration

The log viewer is pre-configured for the Calndr staging environment:

- **CloudWatch Log Group:** `/ecs/calndr-staging`
- **AWS Region:** `us-east-1`
- **Port:** `8001`
- **Health Filter:** Enabled by default

## Controls

- **Hide Health Checks Toggle:** Show/hide GET /health events
- **Clear Logs Button:** Reset the log display  
- **Auto-scroll:** Automatically scrolls to new logs (disabled when manually scrolling up)

## Log Levels

Logs are color-coded by level:
- 🔴 **ERROR** - Red background
- 🟡 **WARNING** - Orange background  
- 🟣 **DEBUG** - Purple background
- 🔵 **INFO** - Blue text (default)

## Dependencies

- FastAPI + uvicorn for the web server
- boto3 for CloudWatch integration
- WebSockets for real-time communication

## Troubleshooting

### AWS Credentials Issues
```bash
# Set up AWS credentials file
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

### Connection Issues
- Check if the ECS service is running
- Verify the log group `/ecs/calndr-staging` exists in us-east-1
- Check AWS permissions for CloudWatch logs

### Port Already in Use
```bash
# Kill any existing process on port 8001
lsof -ti:8001 | xargs kill -9
```

## Architecture

```
Browser (WebSocket) ↔ FastAPI Server ↔ CloudWatch Logs
                                    ↓
                            Real-time streaming
```

The service polls CloudWatch every 2 seconds for new logs and broadcasts them to all connected browser clients via WebSockets. 