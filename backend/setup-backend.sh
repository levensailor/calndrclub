#!/bin/bash
# Script to set up the refactored application on the EC2 instance.
# This script is intended to be run on the server.
set -e

APP_DIR="/var/www/cal-app"
APP_USER="ec2-user"
SOURCE_DIR="/home/$APP_USER/backend"
LOG_DIR="$APP_DIR/logs"

echo "--- Starting setup for refactored backend on the server ---"

# 1. Install dependencies
echo "--- Installing system packages ---"

# Detect package manager
if command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
    echo "Using dnf package manager (Amazon Linux 2023+)"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum" 
    echo "Using yum package manager (Amazon Linux 2)"
else
    PKG_MGR="yum"
    echo "Defaulting to yum package manager"
fi

sudo $PKG_MGR update -y
sudo $PKG_MGR install -y python3-pip python3-devel nginx certbot python3-certbot-nginx cronie

# Install Redis - try multiple methods for different Amazon Linux versions
echo "--- Installing Redis ---"
REDIS_INSTALLED=false

# Method 1: Amazon Linux Extras (AL2 only)
if sudo amazon-linux-extras list &>/dev/null && sudo amazon-linux-extras list | grep -q redis; then
    echo "Installing Redis via amazon-linux-extras..."
    if sudo amazon-linux-extras install -y redis6; then
        REDIS_INSTALLED=true
    fi
fi

# Method 2: Direct package manager install (AL2023 and others)
if [ "$REDIS_INSTALLED" = false ]; then
    echo "Installing Redis via $PKG_MGR..."
    if sudo $PKG_MGR install -y redis; then
        REDIS_INSTALLED=true
    fi
fi

# Method 3: EPEL repository (AL2 only)
if [ "$REDIS_INSTALLED" = false ] && [ "$PKG_MGR" = "yum" ]; then
    echo "Installing Redis via EPEL repository..."
    if sudo yum install -y epel-release; then
        if sudo yum install -y redis; then
            REDIS_INSTALLED=true
        fi
    fi
fi

# Method 4: Compile from source as last resort
if [ "$REDIS_INSTALLED" = false ]; then
    echo "Installing Redis from source..."
    sudo $PKG_MGR install -y gcc make tcl
    cd /tmp
    wget http://download.redis.io/redis-stable.tar.gz
    tar xzf redis-stable.tar.gz
    cd redis-stable
    make
    sudo make install
    
    # Create Redis user and directories
    sudo useradd -r -s /bin/false redis || true
    sudo mkdir -p /var/lib/redis /var/log/redis /etc/redis
    sudo chown redis:redis /var/lib/redis /var/log/redis
    
    # Create systemd service file
    sudo bash -c "cat > /etc/systemd/system/redis.service" << 'REDIS_SERVICE_EOF'
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
User=redis
Group=redis
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf --supervised systemd --daemonize no
ExecStop=/usr/local/bin/redis-cli shutdown
Restart=always

[Install]
WantedBy=multi-user.target
REDIS_SERVICE_EOF
    
    sudo systemctl daemon-reload
    REDIS_INSTALLED=true
fi

if [ "$REDIS_INSTALLED" = false ]; then
    echo "ERROR: Failed to install Redis. Application will continue without caching."
fi

# 2. Create app directory and set permissions
echo "--- Creating application directory and setting permissions ---"
sudo mkdir -p $APP_DIR
sudo rm -rf $APP_DIR/* # Clean out the directory before copying new files

# 3. Copy application files
echo "--- Copying application files to $APP_DIR ---"
# Copy the entire backend directory content
if [ -d "$SOURCE_DIR" ]; then
    sudo cp -r $SOURCE_DIR/* $APP_DIR/
fi
# Copy other files that were rsynced to home
[ -f /home/$APP_USER/.env ] && sudo cp /home/$APP_USER/.env $APP_DIR/
[ -f /home/$APP_USER/AuthKey_RZ6KL226Z5.p8 ] && sudo cp /home/$APP_USER/AuthKey_RZ6KL226Z5.p8 $APP_DIR/

# 4. Create logs directory
sudo mkdir -p $LOG_DIR

# 5. Set ownership and permissions
sudo chown -R $APP_USER:$APP_USER $APP_DIR
sudo chmod -R 755 $APP_DIR
sudo chmod 775 $LOG_DIR

cd $APP_DIR

# 6. Create python virtual environment and install packages
echo "--- Creating Python virtual environment and installing dependencies ---"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi
deactivate

# 7. Configure and start Redis (only if Redis was installed)
if [ "$REDIS_INSTALLED" = true ]; then
echo "--- Configuring Redis for local caching ---"
# Create Redis configuration directory and file
sudo mkdir -p /etc/redis

# Backup any existing config
if [ -f "/etc/redis.conf" ]; then
    echo "Backing up existing Redis config..."
    sudo cp /etc/redis.conf /etc/redis/redis.conf.backup
fi

sudo bash -c "cat > /etc/redis/redis.conf" << REDIS_EOF
# Basic Redis configuration for calndr app caching
bind 127.0.0.1
port 6379
timeout 300
tcp-keepalive 60

# Security settings
protected-mode yes
# requirepass your_redis_password_here  # Uncomment and set password for production

# Memory management
maxmemory 128mb
maxmemory-policy allkeys-lru

# Persistence - disabled for cache-only usage
save ""
appendonly no

# Logging
loglevel notice
logfile /var/log/redis/redis.log

# Working directory
dir /var/lib/redis

# Performance tuning
tcp-backlog 511
databases 1
REDIS_EOF

# Create Redis directories and set permissions
sudo mkdir -p /var/lib/redis /var/log/redis
sudo chown redis:redis /var/lib/redis /var/log/redis
sudo chmod 755 /var/lib/redis /var/log/redis

# Update Redis systemd service to use our config file
echo "--- Updating Redis systemd service configuration ---"
if [ -f "/etc/systemd/system/redis.service" ]; then
    # If we created our own service file (from source install), it should already be correct
    echo "Using custom Redis service file"
else
    # For package-installed Redis, update the service to use our config
    sudo mkdir -p /etc/systemd/system/redis.service.d
    sudo bash -c "cat > /etc/systemd/system/redis.service.d/override.conf" << SERVICE_OVERRIDE_EOF
[Service]
ExecStart=
ExecStart=/usr/bin/redis-server /etc/redis/redis.conf --supervised systemd --daemonize no
SERVICE_OVERRIDE_EOF
fi

sudo systemctl daemon-reload

# Start and enable Redis service
echo "--- Starting Redis service ---"
sudo systemctl start redis
sudo systemctl enable redis

# Test Redis connection
echo "--- Testing Redis connection ---"
if redis-cli ping | grep -q "PONG"; then
    echo "✓ Redis is running and responding"
else
    echo "✗ Redis connection failed"
    sudo systemctl status redis --no-pager
fi

else
    echo "--- Skipping Redis configuration (Redis not installed) ---"
    echo "Application will run without caching capabilities"
fi

# 8. Create a simple health check endpoint if it doesn't exist
echo "--- Ensuring health check endpoint exists ---"
if ! grep -q "health" main.py; then
    echo "Adding health endpoint to main.py..."
    sudo bash -c "cat >> main.py" << 'HEALTH_EOF'

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "calndr-backend"}
HEALTH_EOF
fi

# 8. Set up systemd service to run gunicorn with PYTHONPATH
echo "--- Creating systemd service file for refactored app ---"
sudo bash -c "cat > /etc/systemd/system/cal-app.service" << EOL
[Unit]
Description=Gunicorn instance to serve the calendar app
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PYTHONPATH=$APP_DIR"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --access-logfile $LOG_DIR/access.log --error-logfile $LOG_DIR/error.log main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# 9. Set up nginx as a reverse proxy
echo "--- Configuring nginx ---"
sudo bash -c "cat > /etc/nginx/conf.d/cal-app.conf" << EOL
# HTTP server - redirect to HTTPS
server {
    listen 80;
    server_name calndr.club www.calndr.club;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name calndr.club www.calndr.club;

    # SSL Configuration (will be managed by certbot)
    ssl_certificate /etc/letsencrypt/live/calndr.club/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calndr.club/privkey.pem;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Increase timeouts for large requests
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;
    send_timeout 120s;

    # Increase buffer sizes
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    proxy_buffer_size 4k;
    proxy_buffers 8 16k;
    proxy_busy_buffers_size 32k;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }

    location /db-info {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }

    location /cache-status {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
    }
}
EOL

# Remove default nginx config if it exists
sudo rm -f /etc/nginx/conf.d/default.conf

# Create initial nginx config without SSL for certbot
echo "--- Creating temporary nginx config for SSL certificate generation ---"
sudo bash -c "cat > /etc/nginx/conf.d/cal-app-temp.conf" << EOL
server {
    listen 80;
    server_name calndr.club www.calndr.club;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

sudo nginx -t

# 10. Start and enable services
echo "--- Starting and enabling services ---"
sudo systemctl daemon-reload
sudo systemctl restart cal-app
sudo systemctl enable cal-app

# Start nginx with temporary config for SSL generation
sudo systemctl restart nginx
sudo systemctl enable nginx

# Create web root for acme challenge
sudo mkdir -p /var/www/html
sudo chown -R nginx:nginx /var/www/html

# 11. Obtain SSL certificate with Certbot if not already obtained
echo "--- Checking for existing SSL certificate ---"
if ! sudo certbot certificates 2>/dev/null | grep -q "calndr.club"; then
    echo "--- Obtaining SSL certificate with Certbot ---"
    
    # Stop nginx temporarily to avoid conflicts
    sudo systemctl stop nginx
    
    # Use standalone mode for initial certificate generation
    sudo certbot certonly --standalone \
        -d calndr.club \
        -d www.calndr.club \
        --non-interactive \
        --agree-tos \
        --email jeff@levensailor.com \
        --preferred-challenges http
    
    if [ $? -eq 0 ]; then
        echo "--- SSL certificate obtained successfully ---"
        
        # Remove temporary nginx config and use the full HTTPS config
        sudo rm -f /etc/nginx/conf.d/cal-app-temp.conf
        
        # Test nginx configuration
        sudo nginx -t
        
        # Start nginx with HTTPS configuration
        sudo systemctl start nginx
    else
        echo "--- Failed to obtain SSL certificate, keeping HTTP-only configuration ---"
        # Keep the temporary config for HTTP-only operation
        sudo systemctl start nginx
    fi
else
    echo "--- SSL certificate already exists ---"
    # Remove temporary config and use HTTPS config
    sudo rm -f /etc/nginx/conf.d/cal-app-temp.conf
    sudo nginx -t
    sudo systemctl restart nginx
fi

# 12. Set up enhanced automatic certificate renewal
echo "--- Setting up enhanced automatic certificate renewal ---"

# Create a custom renewal script for better logging and error handling
sudo bash -c "cat > /usr/local/bin/renew-ssl-certs.sh" << 'RENEWAL_EOF'
#!/bin/bash
# Enhanced SSL certificate renewal script with logging

LOG_FILE="/var/log/ssl-renewal.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting SSL certificate renewal check..." >> $LOG_FILE

# Test nginx configuration before renewal
if ! nginx -t >> $LOG_FILE 2>&1; then
    echo "[$DATE] ERROR: nginx configuration test failed, skipping renewal" >> $LOG_FILE
    exit 1
fi

# Attempt renewal
if certbot renew --nginx --quiet >> $LOG_FILE 2>&1; then
    echo "[$DATE] Certificate renewal check completed successfully" >> $LOG_FILE
    
    # Test nginx configuration after renewal
    if nginx -t >> $LOG_FILE 2>&1; then
        systemctl reload nginx >> $LOG_FILE 2>&1
        echo "[$DATE] nginx reloaded successfully" >> $LOG_FILE
    else
        echo "[$DATE] ERROR: nginx configuration test failed after renewal" >> $LOG_FILE
        exit 1
    fi
else
    echo "[$DATE] Certificate renewal failed or no renewal needed" >> $LOG_FILE
fi

# Clean up old log entries (keep last 30 days)
find /var/log -name "ssl-renewal.log*" -mtime +30 -delete 2>/dev/null || true

echo "[$DATE] SSL renewal process completed" >> $LOG_FILE
RENEWAL_EOF

# Make the renewal script executable
sudo chmod +x /usr/local/bin/renew-ssl-certs.sh

# Create systemd service for renewal
sudo bash -c "cat > /etc/systemd/system/ssl-renewal.service" << EOL
[Unit]
Description=Renew SSL certificates
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/renew-ssl-certs.sh
User=root
EOL

# Create systemd timer for automatic renewal (twice daily)
sudo bash -c "cat > /etc/systemd/system/ssl-renewal.timer" << EOL
[Unit]
Description=Run SSL certificate renewal twice daily
Requires=ssl-renewal.service

[Timer]
OnCalendar=*-*-* 02,14:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOL

# Enable and start the renewal timer
sudo systemctl daemon-reload
sudo systemctl enable ssl-renewal.timer
sudo systemctl start ssl-renewal.timer

# Also set up a weekly renewal check via cron as backup
echo "--- Setting up backup cron job for SSL renewal ---"
(sudo crontab -l 2>/dev/null; echo "0 3 * * 1 /usr/local/bin/renew-ssl-certs.sh") | sudo crontab -

# 13. Configure firewall for HTTPS traffic
echo "--- Configuring firewall for HTTPS traffic ---"
# Check if firewalld is running
if sudo systemctl is-active --quiet firewalld; then
    echo "Configuring firewalld..."
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --permanent --add-port=8000/tcp
    sudo firewall-cmd --reload
    echo "Firewall configured for HTTP, HTTPS, and backend port 8000"
elif command -v ufw &> /dev/null; then
    echo "Configuring UFW..."
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 8000/tcp
    sudo ufw --force enable
    echo "UFW configured for HTTP, HTTPS, and backend port 8000"
else
    echo "No firewall detected or firewall not active. Ensure ports 80, 443, and 8000 are open."
fi

# 14. Check service status
echo "--- Checking service status ---"
sudo systemctl status cal-app --no-pager || true

# 15. Verify SSL certificate status
echo "--- Checking SSL certificate status ---"
if [ -f "/etc/letsencrypt/live/calndr.club/fullchain.pem" ]; then
    echo "SSL certificate found. Checking expiration..."
    sudo openssl x509 -in /etc/letsencrypt/live/calndr.club/fullchain.pem -text -noout | grep "Not After" || true
    echo "SSL renewal timer status:"
    sudo systemctl status ssl-renewal.timer --no-pager || true
else
    echo "SSL certificate not found. HTTPS may not be available."
fi

# 16. Show final status and instructions
echo ""
echo "--- Deployment to EC2 finished successfully! ---"
echo ""
if [ -f "/etc/letsencrypt/live/calndr.club/fullchain.pem" ]; then
    echo "🔒 Your app is available at:"
    echo "  - HTTPS: https://calndr.club (recommended)"
    echo "  - HTTPS: https://www.calndr.club"
    echo "  - HTTP requests will automatically redirect to HTTPS"
    echo ""
    echo "🔐 SSL Certificate Status:"
    echo "  - Auto-renewal: ENABLED (runs twice daily at 2:00 AM and 2:00 PM)"
    echo "  - Backup renewal: ENABLED (weekly via cron)"
    echo "  - Certificate expires: $(sudo openssl x509 -in /etc/letsencrypt/live/calndr.club/fullchain.pem -text -noout | grep "Not After" | sed 's/.*Not After : //')"
else
    echo "⚠️  Your app is available at:"
    echo "  - HTTP: http://calndr.club"
    echo "  - HTTP: http://www.calndr.club"
    echo "  - HTTPS setup failed - check logs for details"
fi
echo ""
echo "📊 API Endpoints:"
echo "  - Health check: https://calndr.club/health"
if [ "$REDIS_INSTALLED" = true ]; then
    echo "  - Cache status: https://calndr.club/cache-status"
fi
echo "  - API documentation: https://calndr.club/docs"
echo "  - ReDoc: https://calndr.club/redoc"
echo ""
echo "📝 Log files location:"
echo "  - Application logs: $LOG_DIR/backend.log"
echo "  - Access logs: $LOG_DIR/access.log"
echo "  - Error logs: $LOG_DIR/error.log"
echo "  - SSL renewal logs: /var/log/ssl-renewal.log"
echo ""
echo "🔧 Useful commands:"
echo "  - View app logs: sudo tail -f $LOG_DIR/backend.log"
echo "  - View system logs: sudo journalctl -u cal-app -f"
if [ "$REDIS_INSTALLED" = true ]; then
    echo "  - Check Redis status: sudo systemctl status redis"
    echo "  - Monitor Redis: redis-cli monitor"
    echo "  - Redis memory usage: redis-cli info memory"
fi
echo "  - Check SSL status: sudo certbot certificates"
echo "  - Test SSL renewal: sudo certbot renew --dry-run"
echo "  - Check renewal timer: sudo systemctl status ssl-renewal.timer" 