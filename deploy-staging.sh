#!/bin/bash

# Deploy Staging Infrastructure for Calndr Backend
# This script deploys the staging environment infrastructure using Terraform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform"
ENVIRONMENT="staging"

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

# Check if we're in the right directory
if [ ! -f "$TERRAFORM_DIR/main.tf" ]; then
    error "Terraform configuration not found. Please run this script from the project root."
    exit 1
fi

# Check if AWS credentials are available
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    error "AWS credentials not configured. Please run 'aws configure' or set environment variables."
    exit 1
fi

# Check if Terraform backend infrastructure exists
log "Checking Terraform backend infrastructure..."
if ! aws s3api head-bucket --bucket "calndr-terraform-state" 2>/dev/null; then
    warn "Terraform backend not set up. Setting up S3 bucket and DynamoDB table..."
    "$SCRIPT_DIR/terraform/setup-backend.sh"
fi

log "Starting deployment of $ENVIRONMENT infrastructure..."

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    log "Initializing Terraform..."
    terraform init
fi

# Create or switch to staging workspace
log "Setting up Terraform workspace for $ENVIRONMENT..."
terraform workspace select $ENVIRONMENT 2>/dev/null || terraform workspace new $ENVIRONMENT

# Validate configuration
log "Validating Terraform configuration..."
terraform validate

# Plan the deployment
log "Planning infrastructure changes for $ENVIRONMENT..."
terraform plan -var-file="staging.tfvars" -out="staging.tfplan"

# Ask for confirmation
echo
read -p "Do you want to apply these changes? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Deployment cancelled by user."
    exit 0
fi

# Apply the changes
log "Applying infrastructure changes for $ENVIRONMENT..."
terraform apply "staging.tfplan"

# Clean up plan file
rm -f "staging.tfplan"

# Get outputs
log "Deployment completed! Here are the important outputs:"
echo
terraform output -json | jq -r '
    "ECR Repository: " + .ecr_repository_url.value + 
    "\nCluster Name: " + .ecs_cluster_name.value +
    "\nService Name: " + .ecs_service_name.value +
    "\nLoad Balancer DNS: " + .load_balancer_dns.value +
    "\nDatabase Endpoint: " + .database_endpoint.value +
    "\nRedis Endpoint: " + .redis_endpoint.value
'

log "Staging infrastructure deployment completed successfully!"
log "Next steps:"
log "1. Update your application configuration with the outputs above"
log "2. Push code to the 'develop' branch to trigger automatic deployment"
log "3. Monitor the deployment in the AWS Console" 