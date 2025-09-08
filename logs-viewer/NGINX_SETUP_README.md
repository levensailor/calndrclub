# Nginx Setup with SSL for Port 8001

This directory contains scripts to set up Nginx as a reverse proxy with Let's Encrypt SSL certificates to serve applications running on port 8001.

## Scripts Available

### 1. `setup-nginx-ssl.sh` - Full SSL Setup
Complete nginx setup with Let's Encrypt SSL certificates for production use.

**Usage:**
```bash
# For production with SSL
./setup-nginx-ssl.sh yourdomain.com admin@yourdomain.com

# For localhost (no SSL)
./setup-nginx-ssl.sh localhost
```

**Features:**
- ✅ Installs nginx
- ✅ Configures reverse proxy for port 8001
- ✅ Sets up Let's Encrypt SSL certificates
- ✅ Automatic SSL certificate renewal
- ✅ Security headers
- ✅ WebSocket support
- ✅ HTTP to HTTPS redirect

### 2. `setup-nginx-local.sh` - Quick Local Setup
Simplified setup for local development without SSL.

**Usage:**
```bash
# For local development
./setup-nginx-local.sh
```

**Features:**
- ✅ Installs nginx
- ✅ Configures reverse proxy for port 8001
- ✅ WebSocket support
- ✅ No SSL (HTTP only)

## Prerequisites

### For SSL Setup (Production)
- Domain name pointing to your server
- Ports 80 and 443 open in firewall
- Valid email address for Let's Encrypt

### For Local Setup
- Port 80 available locally
- sudo/root access

## Configuration Details

### Nginx Configuration
Both scripts create nginx configurations that:

1. **Proxy all traffic** from port 80/443 to port 8001
2. **Support WebSockets** for real-time applications
3. **Include proper headers** for security and functionality
4. **Handle timeouts** appropriately

### SSL Configuration (Production Only)
- Uses Let's Encrypt certificates
- Implements modern SSL/TLS settings
- Includes security headers (HSTS, X-Frame-Options, etc.)
- Automatic certificate renewal via cron job

## Usage Examples

### Production Deployment
```bash
# 1. Run the SSL setup script
./setup-nginx-ssl.sh myapp.example.com admin@example.com

# 2. Start your application on port 8001
python3 your_app.py  # or whatever starts your service

# 3. Test the setup
curl https://myapp.example.com
```

### Local Development
```bash
# 1. Run the local setup script
./setup-nginx-local.sh

# 2. Start your application on port 8001
python3 your_app.py

# 3. Test the setup
curl http://localhost
```

## Service Management

### Check Nginx Status
```bash
sudo systemctl status nginx
```

### Restart Nginx
```bash
sudo systemctl restart nginx
```

### View Nginx Logs
```bash
# Real-time logs
sudo journalctl -u nginx -f

# Error logs
sudo tail -f /var/log/nginx/error.log

# Access logs
sudo tail -f /var/log/nginx/access.log
```

### Test Configuration
```bash
sudo nginx -t
```

## Troubleshooting

### Common Issues

1. **Port 8001 not responding**
   - Ensure your application is running on port 8001
   - Check if the port is bound to localhost (127.0.0.1:8001)

2. **SSL certificate issues**
   - Verify domain points to your server
   - Check firewall allows ports 80 and 443
   - Ensure no other service is using port 80

3. **WebSocket not working**
   - Check if your application supports WebSockets
   - Verify the `/ws` endpoint is properly configured

### Debug Commands

```bash
# Check what's running on port 8001
sudo netstat -tlnp | grep 8001

# Check nginx configuration
sudo nginx -T

# Test specific endpoint
curl -v http://localhost/health

# Check SSL certificate (if using HTTPS)
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

## File Locations

### Configuration Files
- **Nginx config**: `/etc/nginx/conf.d/calndr-local.conf` (local)
- **Site config**: `/etc/nginx/sites-available/yourdomain.com` (SSL)
- **SSL certificates**: `/etc/letsencrypt/live/yourdomain.com/` (SSL)

### Log Files
- **Nginx logs**: `/var/log/nginx/`
- **System logs**: `journalctl -u nginx`

## Security Considerations

### Production Setup
- ✅ SSL/TLS encryption
- ✅ Security headers
- ✅ HSTS (HTTP Strict Transport Security)
- ✅ Automatic certificate renewal
- ✅ Modern cipher suites

### Local Development
- ⚠️ HTTP only (no encryption)
- ✅ Proper proxy headers
- ✅ WebSocket support

## Integration with CloudWatch Log Viewer

These scripts are specifically designed to work with the CloudWatch Log Viewer application that runs on port 8001. The nginx configuration includes:

- **WebSocket support** for real-time log streaming
- **Proper headers** for FastAPI applications
- **Timeout settings** appropriate for log streaming
- **Security headers** for production deployments

## Next Steps

After running the setup:

1. **Start your application** on port 8001
2. **Test the endpoints** (health check, WebSocket)
3. **Monitor logs** for any issues
4. **Set up monitoring** for production deployments
5. **Configure backup** for SSL certificates

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review nginx logs for errors
3. Test your application independently on port 8001
4. Verify firewall and network configuration
