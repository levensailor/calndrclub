#!/bin/bash
# Script to set up the application on the EC2 instance.
# This script is intended to be run on the server.
set -e

APP_DIR="/var/www/cal-app"
APP_USER="ec2-user"

echo "--- Starting setup on the server ---"

# 1. Install dependencies
echo "--- Installing system packages ---"
sudo yum update -y
sudo yum install -y python3-pip python3-devel nginx certbot python3-certbot-nginx cronie

# 2. Create app directory and set permissions
echo "--- Creating application directory and setting permissions ---"
sudo mkdir -p $APP_DIR

# Move files from home directory if they exist, replacing old ones
[ -f /home/$APP_USER/app.py ] && sudo mv -f /home/$APP_USER/app.py $APP_DIR/
[ -f /home/$APP_USER/requirements.txt ] && sudo mv -f /home/$APP_USER/requirements.txt $APP_DIR/
[ -f /home/$APP_USER/.env ] && sudo mv -f /home/$APP_USER/.env $APP_DIR/.env
# [ -f /home/$APP_USER/send_weekly_email.py ] && sudo mv -f /home/$APP_USER/send_weekly_email.py $APP_DIR/
[ -f /home/$APP_USER/setup.sh ] && sudo mv -f /home/$APP_USER/setup.sh $APP_DIR/
# [ -f /home/$APP_USER/initial_setup.py ] && sudo mv -f /home/$APP_USER/initial_setup.py $APP_DIR/
# [ -f /home/$APP_USER/migrate_user_profile.py ] && sudo mv -f /home/$APP_USER/migrate_user_profile.py $APP_DIR/
# [ -f /home/$APP_USER/migrate_notification_emails.py ] && sudo mv -f /home/$APP_USER/migrate_notification_emails.py $APP_DIR/
# [ -f /home/$APP_USER/migrate_custody_table.py ] && sudo mv -f /home/$APP_USER/migrate_custody_table.py $APP_DIR/
# [ -f /home/$APP_USER/migrate_events_table.py ] && sudo mv -f /home/$APP_USER/migrate_events_table.py $APP_DIR/

# Remove old directory before moving the new one
# [ -d /home/$APP_USER/dist ] && sudo rm -rf $APP_DIR/dist && sudo mv /home/$APP_USER/dist $APP_DIR/

sudo chown -R $APP_USER:$APP_USER $APP_DIR
cd $APP_DIR

# 3. Create python virtual environment and install packages
echo "--- Creating Python virtual environment and installing dependencies ---"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# 4. Set up systemd service to run gunicorn
echo "--- Creating systemd service file ---"
sudo bash -c "cat > /etc/systemd/system/cal-app.service" << EOL
[Unit]
Description=Gunicorn instance to serve the calendar app
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker app:app

[Install]
WantedBy=multi-user.target
EOL

# 5. Set up nginx as a reverse proxy
echo "--- Configuring nginx ---"
sudo bash -c "cat > /etc/nginx/conf.d/cal-app.conf" << EOL
server {
    listen 80;
    server_name calndr.club; # Use your domain name here

    # Serve static files directly
    location / {
        root $APP_DIR/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }

    # Proxy API calls to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Proxy health endpoint to FastAPI backend
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Add proper headers for static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        root $APP_DIR/dist;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOL

# Remove default nginx config if it exists
sudo rm -f /etc/nginx/conf.d/default.conf
sudo nginx -t # Test nginx configuration

# 6. Start and enable services
echo "--- Starting and enabling services ---"
sudo systemctl daemon-reload
sudo systemctl restart cal-app
sudo systemctl enable cal-app
sudo systemctl restart nginx
sudo systemctl enable nginx

# 7. Obtain SSL certificate with Certbot
echo "--- Obtaining SSL certificate with Certbot ---"
# This command obtains a cert for your domain, automatically configures nginx,
# and sets up a redirect from HTTP to HTTPS.
sudo certbot --nginx -d calndr.club --non-interactive --agree-tos --email jeff@levensailor.com --redirect

# 8. Enable automatic certificate renewal
echo "--- Enabling automatic certificate renewal ---"
sudo systemctl start certbot-renew.timer
sudo systemctl enable certbot-renew.timer

# # Create .env file with secrets
# echo "Creating .env file on the server..."
# cat << EOF > /var/www/cal-app/.env
# DB_USER=postgres
# DB_PASSWORD=Money4cookies
# DB_HOST=cal-db-instance.cjy8vmu6rtrc.us-east-1.rds.amazonaws.com
# DB_PORT=5432
# DB_NAME=postgres
# SECRET_KEY=minnie_mouse_club_house_is_awesome
# APNS_CERT_PATH=/var/www/cal-app/AuthKey_4LZC88RV85.p8
# EOF

# Make our script executable
# chmod +x /var/www/cal-app/send_weekly_email.py

# Set up cron job for weekly email summary
# This will run the script every Sunday at 18:00 UTC (2 PM EST / 1 PM EDT)
# Note: cron jobs run in a minimal environment, so we source the .env file to get credentials.
# The output (stdout & stderr) is logged to /var/log/cron_weekly_email.log
# CRON_JOB="0 18 * * 0 source /var/www/cal-app/.env; /var/www/cal-app/venv/bin/python3 /var/www/cal-app/send_weekly_email.py >> /var/log/cron_weekly_email.log 2>&1"
# (sudo /usr/bin/crontab -l -u $APP_USER 2>/dev/null | grep -Fv "send_weekly_email.py" || true; echo "$CRON_JOB") | sudo /usr/bin/crontab -u $APP_USER -

# echo "Cron job for weekly email set up."

# 9. Run the initial data seeding script (DISABLED to prevent data loss on deployments)
# echo "--- Running initial database setup script ---"
# sudo -u $APP_USER $APP_DIR/venv/bin/python3 $APP_DIR/initial_setup.py

# 10. Run user profile migration script (DISABLED to prevent data loss on deployments)
# echo "--- Running user profile migration script ---"
# sudo -u $APP_USER $APP_DIR/venv/bin/python3 $APP_DIR/migrate_user_profile.py

# # 11. Run notification emails migration script
# echo "--- Running notification emails migration script ---"
# sudo -u $APP_USER $APP_DIR/venv/bin/python3 $APP_DIR/migrate_notification_emails.py

# # 12. Run custody table migration script
# echo "--- Running custody table migration script ---"
# sudo -u $APP_USER $APP_DIR/venv/bin/python3 $APP_DIR/migrate_custody_table.py

# # 13. Run events table migration script
# echo "--- Running events table migration script ---"
# sudo -u $APP_USER $APP_DIR/venv/bin/python3 $APP_DIR/migrate_events_table.py

sudo systemctl restart cal-app
echo "--- Deployment to EC2 finished successfully! ---"
echo "Your app should be available at https://calndr.club" 