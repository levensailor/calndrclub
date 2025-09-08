#!/bin/bash

# Nginx Setup with Let's Encrypt SSL for Port 8001
# Based on deploy-backend-to-ec2.py nginx configuration

set -e

# Configuration
DOMAIN_NAME="${1:-localhost}"
EMAIL="${2:-admin@example.com}"
SERVICE_PORT=8001
NGINX_CONF_DIR="/etc/nginx/conf.d"
SITES_AVAILABLE="/etc/nginx/sites-available"
SITES_ENABLED="/etc/nginx/sites-enabled"

echo "🚀 Setting up Nginx with Let's Encrypt SSL for port $SERVICE_PORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Domain: $DOMAIN_NAME"
echo "📧 Email: $EMAIL"
echo "🔌 Service Port: $SERVICE_PORT"

# Function to detect OS and install nginx
install_nginx() {
    echo "📦 Installing Nginx..."
    
    if command -v yum &> /dev/null; then
        # Amazon Linux / CentOS / RHEL
        sudo yum update -y
        sudo yum install -y nginx
    elif command -v apt-get &> /dev/null; then
        # Ubuntu / Debian
        sudo apt-get update
        sudo apt-get install -y nginx
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf update -y
        sudo dnf install -y nginx
    else
        echo "❌ Unsupported operating system. Please install nginx manually."
        exit 1
    fi
    
    echo "✅ Nginx installed successfully"
}

# Function to install certbot
install_certbot() {
    echo "🔐 Installing Certbot for Let's Encrypt..."
    
    if command -v yum &> /dev/null; then
        # Amazon Linux / CentOS / RHEL
        sudo yum install -y epel-release
        sudo yum install -y certbot python3-certbot-nginx
    elif command -v apt-get &> /dev/null; then
        # Ubuntu / Debian
        sudo apt-get install -y certbot python3-certbot-nginx
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf install -y certbot python3-certbot-nginx
    else
        echo "❌ Unsupported operating system. Please install certbot manually."
        exit 1
    fi
    
    echo "✅ Certbot installed successfully"
}

# Function to create nginx configuration
create_nginx_config() {
    echo "⚙️ Creating Nginx configuration..."
    
    # Create sites-available directory if it doesn't exist
    sudo mkdir -p "$SITES_AVAILABLE"
    sudo mkdir -p "$SITES_ENABLED"
    
    # Create the nginx configuration file
    sudo tee "$SITES_AVAILABLE/$DOMAIN_NAME" > /dev/null << EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
    # Let's Encrypt challenge location
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server - proxy to port $SERVICE_PORT
server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
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

    echo "✅ Nginx configuration created"
}

# Function to enable the site
enable_site() {
    echo "🔗 Enabling site configuration..."
    
    # Remove default site if it exists
    if [ -f "$SITES_ENABLED/default" ]; then
        sudo rm -f "$SITES_ENABLED/default"
    fi
    
    # Create symlink to enable the site
    sudo ln -sf "$SITES_AVAILABLE/$DOMAIN_NAME" "$SITES_ENABLED/$DOMAIN_NAME"
    
    echo "✅ Site enabled"
}

# Function to test nginx configuration
test_nginx_config() {
    echo "🧪 Testing Nginx configuration..."
    
    if sudo nginx -t; then
        echo "✅ Nginx configuration is valid"
        return 0
    else
        echo "❌ Nginx configuration has errors"
        return 1
    fi
}

# Function to start and enable nginx
start_nginx() {
    echo "🚀 Starting and enabling Nginx..."
    
    sudo systemctl start nginx
    sudo systemctl enable nginx
    sudo systemctl reload nginx
    
    echo "✅ Nginx started and enabled"
}

# Function to obtain SSL certificate
obtain_ssl_certificate() {
    echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
    
    # Create web root directory
    sudo mkdir -p /var/www/html
    
    # Stop nginx temporarily for certificate generation
    sudo systemctl stop nginx
    
    # Obtain certificate
    if sudo certbot certonly \
        --webroot \
        --webroot-path=/var/www/html \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --domains "$DOMAIN_NAME"; then
        echo "✅ SSL certificate obtained successfully"
    else
        echo "❌ Failed to obtain SSL certificate"
        echo "⚠️ Continuing with HTTP-only configuration..."
        return 1
    fi
}

# Function to create HTTP-only fallback configuration
create_http_fallback() {
    echo "🌐 Creating HTTP-only fallback configuration..."
    
    sudo tee "$SITES_AVAILABLE/$DOMAIN_NAME" > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
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

    echo "✅ HTTP-only configuration created"
}

# Function to setup SSL certificate renewal
setup_ssl_renewal() {
    echo "🔄 Setting up SSL certificate auto-renewal..."
    
    # Create renewal script
    sudo tee /usr/local/bin/renew-ssl.sh > /dev/null << 'EOF'
#!/bin/bash
# SSL Certificate Renewal Script

echo "🔄 Checking SSL certificate renewal..."
if certbot renew --quiet; then
    echo "✅ SSL certificate renewed successfully"
    systemctl reload nginx
else
    echo "❌ SSL certificate renewal failed"
fi
EOF

    sudo chmod +x /usr/local/bin/renew-ssl.sh
    
    # Add cron job for automatic renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/local/bin/renew-ssl.sh") | crontab -
    
    echo "✅ SSL certificate auto-renewal configured"
}

# Main execution
main() {
    echo "🚀 Starting Nginx setup with SSL for port $SERVICE_PORT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Install nginx
    install_nginx
    
    # Create nginx configuration
    create_nginx_config
    
    # Enable the site
    enable_site
    
    # Test configuration
    if ! test_nginx_config; then
        echo "❌ Nginx configuration test failed. Exiting."
        exit 1
    fi
    
    # Start nginx
    start_nginx
    
    # Check if domain is not localhost
    if [ "$DOMAIN_NAME" != "localhost" ]; then
        # Install certbot
        install_certbot
        
        # Try to obtain SSL certificate
        if obtain_ssl_certificate; then
            # Update configuration for HTTPS
            create_nginx_config
            enable_site
            
            # Test and restart nginx
            if test_nginx_config; then
                start_nginx
                setup_ssl_renewal
                echo "✅ HTTPS configuration completed"
            else
                echo "❌ HTTPS configuration failed, falling back to HTTP"
                create_http_fallback
                enable_site
                start_nginx
            fi
        else
            echo "⚠️ SSL certificate generation failed, using HTTP-only configuration"
            create_http_fallback
            enable_site
            start_nginx
        fi
    else
        echo "ℹ️ Using localhost - skipping SSL certificate generation"
        create_http_fallback
        enable_site
        start_nginx
    fi
    
    echo ""
    echo "✅ Nginx setup completed successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Service URL: http://$DOMAIN_NAME"
    if [ "$DOMAIN_NAME" != "localhost" ]; then
        echo "🔒 HTTPS URL: https://$DOMAIN_NAME"
    fi
    echo "🔌 Backend Port: $SERVICE_PORT"
    echo "📊 WebSocket: ws://$DOMAIN_NAME/ws"
    echo ""
    echo "📝 Next Steps:"
    echo "   1. Ensure your service is running on port $SERVICE_PORT"
    echo "   2. Test the configuration: curl http://$DOMAIN_NAME"
    if [ "$DOMAIN_NAME" != "localhost" ]; then
        echo "   3. Test HTTPS: curl https://$DOMAIN_NAME"
        echo "   4. SSL certificate will auto-renew via cron job"
    fi
    echo "   5. Check nginx status: sudo systemctl status nginx"
    echo "   6. View nginx logs: sudo journalctl -u nginx -f"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root. It will use sudo when needed."
    exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <domain_name> [email]"
    echo "Example: $0 example.com admin@example.com"
    echo "Example: $0 localhost (for local development)"
    exit 1
fi

# Run main function
main
