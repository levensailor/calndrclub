#!/bin/bash
set -e

# Configuration
SERVER_IP="54.80.82.14"
SSH_USER="ec2-user"
PEM_KEY="~/.ssh/aws-2024.pem"
REMOTE_DIR="/home/ec2-user"
LOCAL_DIR="./backend"
APP_DIR="/var/www/cal-app"

# --- Main Deployment Function ---
deploy() {
    echo "--- Starting deployment of refactored backend to EC2 instance $SERVER_IP ---"
    
    # --- Configuration ---
    # EC2_HOST="54.80.82.14"
    # EC2_USER="ec2-user"
    # --- IMPORTANT: Update this if your key is in a different location ---
    # KEY_PAIR_FILE="~/.ssh/aws-2024.pem"

    # --- Check for key file ---
    KEY_PAIR_PATH=$(eval echo "$PEM_KEY")
    if [ ! -f "$KEY_PAIR_PATH" ]; then
        echo "ERROR: Key pair file not found at $KEY_PAIR_PATH"
        echo "Please update the KEY_PAIR_FILE variable in this script."
        exit 1
    fi

    # --- Check for .env file ---
    if [ ! -f ".env" ]; then
        echo "WARNING: .env file not found in current directory"
        echo "The application will not work properly without environment variables"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    echo "--- Cleaning up remote directories ---"
    ssh -i "$PEM_KEY" "$SSH_USER@$SERVER_IP" "rm -rf ~/backend"

    echo "--- Preparing backend directory structure ---"
    mkdir -p backend/logs

    echo "--- Copying backend files to server ---"
    rsync -avz \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude 'venv' \
        --exclude '.git' \
        --exclude '.pytest_cache' \
        --exclude '*.log' \
        -e "ssh -i $PEM_KEY" \
        backend/ "${SSH_USER}@${SERVER_IP}:~/backend/"

    echo "--- Copying setup script ---"
    rsync -avz -e "ssh -i $PEM_KEY" backend/setup-backend.sh "${SSH_USER}@${SERVER_IP}:~/backend/"

    if [ -f ".env" ]; then
        echo "--- Copying environment variables ---"
        rsync -avz -e "ssh -i $PEM_KEY" .env "${SSH_USER}@${SERVER_IP}:~/"
    fi

    if [ -f "AuthKey_RZ6KL226Z5.p8" ]; then
        echo "--- Copying APNs authentication key ---"
        rsync -avz -e "ssh -i $PEM_KEY" AuthKey_RZ6KL226Z5.p8 "${SSH_USER}@${SERVER_IP}:~/"
    fi

    echo "--- Running setup script on server ---"
    ssh -i "$PEM_KEY" "$SSH_USER@$SERVER_IP" "chmod +x ~/backend/setup-backend.sh && ~/backend/setup-backend.sh"

    echo "--- Checking service status ---"
    ssh -i "$PEM_KEY" "$SSH_USER@$SERVER_IP" "sudo systemctl status cal-app --no-pager" || true

    echo "--- Deployment finished ---"
    echo "Check the output from the server above to ensure there were no errors."
    echo "If successful, your application should be available at https://calndr.club"

    echo "--- Testing deployment ---"
    echo "Checking API health endpoint..."
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://calndr.club/health || echo "API might not be ready yet"
    
    echo "--- Optional: Database Index Optimization ---"
    echo "To optimize database performance (70-80% faster queries), run:"
    echo "  python migrate_optimize_indexes.py"
    echo "This is safe to run anytime and takes 5-15 minutes."
}

# --- Utility Functions ---
view_logs() {
    echo "--- Tailing backend logs ---"
    ssh -i "$PEM_KEY" "$SSH_USER@$SERVER_IP" "tail -f /var/www/cal-app/logs/backend.log"
}

restart_services() {
    echo "--- Restarting services ---"
    ssh -i "$PEM_KEY" "$SSH_USER@$SERVER_IP" "sudo systemctl restart cal-app nginx"
}

# --- Script Logic ---
if [ "$1" == "view" ]; then
    view_logs
elif [ "$1" == "restart" ]; then
    restart_services
else
    deploy
fi 