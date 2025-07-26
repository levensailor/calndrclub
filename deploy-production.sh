#!/bin/bash

# Deploy Production Infrastructure for Calndr Backend
# This script deploys the production environment infrastructure using Terraform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform"
ENVIRONMENT="production"

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

# Extra confirmation for production
warn "You are about to deploy PRODUCTION infrastructure!"
warn "This will create real AWS resources that may incur costs."
echo
read -p "Are you absolutely sure you want to proceed with PRODUCTION deployment? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Production deployment cancelled by user."
    exit 0
fi

log "Starting deployment of $ENVIRONMENT infrastructure..."

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    log "Initializing Terraform..."
    terraform init
fi

# Create or switch to production workspace
log "Setting up Terraform workspace for $ENVIRONMENT..."
terraform workspace select $ENVIRONMENT 2>/dev/null || terraform workspace new $ENVIRONMENT

# Validate configuration
log "Validating Terraform configuration..."
terraform validate

# Plan the deployment
log "Planning infrastructure changes for $ENVIRONMENT..."
terraform plan -var-file="production.tfvars" -out="production.tfplan"

# Final confirmation
echo
warn "FINAL CONFIRMATION: This will deploy PRODUCTION infrastructure with real costs!"
read -p "Type 'DEPLOY PRODUCTION' to confirm: " -r
if [[ $REPLY != "DEPLOY PRODUCTION" ]]; then
    log "Production deployment cancelled by user."
    rm -f "production.tfplan"
    exit 0
fi

# Apply the changes
log "Applying infrastructure changes for $ENVIRONMENT..."
terraform apply "production.tfplan"

# Clean up plan file
rm -f "production.tfplan"

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

log "Production infrastructure deployment completed successfully!"
log "IMPORTANT: Make sure to:"
log "1. Update DNS records to point to the load balancer"
log "2. Configure SSL certificates if not already done"
log "3. Update monitoring and alerting"
log "4. Test the deployment thoroughly before announcing"
log "5. Push code to the 'main' branch to trigger automatic deployment" 