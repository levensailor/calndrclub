# Deployment Guide for Calndr Backend

This guide explains how to deploy the refactored Calndr backend to AWS EC2.

## Prerequisites

1. **AWS EC2 Instance**
   - Amazon Linux 2 AMI
   - Instance with public IP: 54.80.82.14
   - Security group with ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) open

2. **SSH Key**
   - Private key file: `~/.ssh/aws-2024.pem`
   - Proper permissions: `chmod 400 ~/.ssh/aws-2024.pem`

3. **Domain**
   - Domain name: calndr.club
   - DNS A record pointing to EC2 instance IP

4. **Environment Variables**
   - `.env` file in project root with all required variables
   - APNs key file: `AuthKey_RZ6KL226Z5.p8` (if using push notifications)

## Deployment Scripts

### 1. `deploy.sh` - Main Deployment Script

Located in the project root, this script:
- Validates prerequisites (SSH key, .env file)
- Creates logs directory structure
- Copies backend files to EC2 instance
- Excludes unnecessary files (cache, venv, logs)
- Copies environment variables and APNs key
- Executes the setup script on the server
- Tests the deployment with health check

**Usage:**
```bash
./deploy.sh
```

### 2. `backend/setup-backend.sh` - Server Setup Script

Runs on the EC2 instance to:
- Install system dependencies
- Set up Python virtual environment
- Install Python packages
- Configure systemd service with proper PYTHONPATH
- Set up Nginx as reverse proxy
- Configure SSL with Let's Encrypt
- Enable log rotation
- Start and enable services

## Key Features of the Deployment

### 1. **PYTHONPATH Configuration**
The systemd service includes `Environment="PYTHONPATH=/var/www/cal-app"` to ensure proper module imports.

### 2. **Logging**
- Application logs: `/var/www/cal-app/logs/backend.log`
- Access logs: `/var/www/cal-app/logs/access.log`
- Error logs: `/var/www/cal-app/logs/error.log`
- Systemd logs: `sudo journalctl -u cal-app -f`

### 3. **Nginx Configuration**
- Proxies `/api/*` requests to Gunicorn
- Includes `/health` endpoint for monitoring
- Exposes `/docs`, `/redoc`, and `/openapi.json` for API documentation
- Increased timeouts and buffer sizes for large requests
- SSL redirect with Let's Encrypt

### 4. **Service Management**
- Service name: `cal-app`
- Auto-restart on failure
- 4 Gunicorn workers with Uvicorn
- 120-second timeout for long-running requests

## Deployment Process

1. **Prepare Environment**
   ```bash
   # Ensure .env file exists
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Run Deployment**
   ```bash
   ./deploy.sh
   ```

3. **Monitor Deployment**
   The script will show:
   - File transfer progress
   - Setup script output
   - Service status
   - Health check result

4. **Verify Deployment**
   - Check API: `curl https://calndr.club/health`
   - View API docs: https://calndr.club/docs
   - Check logs: `ssh -i ~/.ssh/aws-2024.pem ec2-user@54.80.82.14`
     ```bash
     sudo journalctl -u cal-app -f
     sudo tail -f /var/www/cal-app/logs/backend.log
     ```

## Troubleshooting

### Service Won't Start
```bash
# SSH into server
ssh -i ~/.ssh/aws-2024.pem ec2-user@54.80.82.14

# Check service status
sudo systemctl status cal-app

# Check logs
sudo journalctl -u cal-app -n 100

# Test Python imports manually
cd /var/www/cal-app
source venv/bin/activate
export PYTHONPATH=/var/www/cal-app
python -c "from main import app"
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R ec2-user:ec2-user /var/www/cal-app

# Fix permissions
sudo chmod -R 755 /var/www/cal-app
sudo chmod 775 /var/www/cal-app/logs
```

### Nginx Issues
```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Restart nginx
sudo systemctl restart nginx
```

### SSL Certificate Issues
```bash
# Renew certificate manually
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

## Rolling Back

If deployment fails:
1. The previous version remains at `/var/www/cal-app.backup` (if implemented)
2. Database changes are backward compatible
3. Restart the old service: `sudo systemctl restart cal-app`

## Security Considerations

1. **Environment Variables**: Stored in `.env` file with restricted permissions
2. **SSL/TLS**: Enforced via Let's Encrypt and Nginx redirect
3. **Firewall**: Only necessary ports open in AWS security group
4. **Updates**: Regular system updates via `yum update`
5. **Logging**: Sensitive data excluded from logs

## Monitoring

1. **Health Check**: `https://calndr.club/health`
2. **Systemd Status**: `systemctl status cal-app`
3. **Log Monitoring**: Set up CloudWatch or similar for production
4. **Uptime Monitoring**: Consider services like UptimeRobot

## Future Improvements

1. **Blue-Green Deployment**: Zero-downtime deployments
2. **Database Migrations**: Automated migration scripts
3. **Backup Strategy**: Regular backups of data and configurations
4. **CI/CD Pipeline**: GitHub Actions for automated deployments
5. **Container Deployment**: Docker/ECS for better scalability