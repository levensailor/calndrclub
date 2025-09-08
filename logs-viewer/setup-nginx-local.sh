#!/bin/bash

# Quick Nginx Setup for Local Development (Port 8001)
# Simplified version without SSL for local testing

set -e

SERVICE_PORT=8001
NGINX_CONF_DIR="/etc/nginx/conf.d"

echo "🚀 Setting up Nginx for local development on port $SERVICE_PORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Install nginx
echo "📦 Installing Nginx..."
if command -v yum &> /dev/null; then
    sudo yum update -y
    sudo yum install -y nginx
elif command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y nginx
elif command -v dnf &> /dev/null; then
    sudo dnf update -y
    sudo dnf install -y nginx
else
    echo "❌ Unsupported OS. Please install nginx manually."
    exit 1
fi

# Create nginx configuration
echo "⚙️ Creating Nginx configuration..."
sudo tee "$NGINX_CONF_DIR/calndr-local.conf" > /dev/null << EOF
server {
    listen 80;
    server_name localhost;
    
    # Proxy configuration for port $SERVICE_PORT
    location / {
        proxy_pass http://localhost:$SERVICE_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket support
    location /ws {
        proxy_pass http://localhost:$SERVICE_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Test configuration
echo "🧪 Testing Nginx configuration..."
if sudo nginx -t; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    exit 1
fi

# Start and enable nginx
echo "🚀 Starting Nginx..."
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl reload nginx

echo ""
echo "✅ Nginx setup completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Service URL: http://localhost"
echo "🔌 Backend Port: $SERVICE_PORT"
echo "📊 WebSocket: ws://localhost/ws"
echo ""
echo "📝 Next Steps:"
echo "   1. Start your service on port $SERVICE_PORT"
echo "   2. Test: curl http://localhost"
echo "   3. Check status: sudo systemctl status nginx"
echo "   4. View logs: sudo journalctl -u nginx -f"
