#!/bin/bash

# Switch Terraform to S3 Backend
# This script restores main.tf to use S3 backend with DynamoDB locking

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S EST')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S EST')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S EST')] ERROR: $1${NC}"
}

cd "$SCRIPT_DIR"

# Check if backup exists
if [ ! -f "main-s3.tf.backup" ]; then
    error "No S3 backend backup found. Cannot restore S3 backend."
    error "Please manually configure main.tf with S3 backend settings."
    exit 1
fi

# Restore original main.tf
log "Restoring S3 backend configuration..."
cp main-s3.tf.backup main.tf

# Clean up local state files
if [ -f "terraform.tfstate" ]; then
    warn "Local state file found. Backing up before switching to S3..."
    mv terraform.tfstate terraform.tfstate.local.backup.$(date +%Y%m%d_%H%M%S)
fi

# Clean up .terraform directory to force re-initialization
if [ -d ".terraform" ]; then
    warn "Removing existing .terraform directory..."
    rm -rf .terraform
fi

log "Successfully switched back to S3 backend!"
log ""
log "Next steps:"
log "1. Ensure S3 bucket and DynamoDB table exist (run ./setup-backend.sh if needed)"
log "2. terraform init"
log "3. If you have existing infrastructure, you may need to import state or migrate from local state" 