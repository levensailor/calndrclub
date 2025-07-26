#!/bin/bash

# Setup Terraform Backend Infrastructure
# This script creates the S3 bucket and DynamoDB table needed for Terraform state management

set -e

REGION="us-east-1"
BUCKET_NAME="calndr-terraform-state"
DYNAMODB_TABLE="calndr-terraform-locks"

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

# Check if AWS credentials are available
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    error "AWS credentials not configured. Please run 'aws configure' or set environment variables."
    exit 1
fi

log "Setting up Terraform backend infrastructure..."

# Create S3 bucket for Terraform state
log "Creating S3 bucket: $BUCKET_NAME"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    warn "S3 bucket $BUCKET_NAME already exists"
else
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION" 2>/dev/null || \
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION"
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled
    
    # Enable server-side encryption
    aws s3api put-bucket-encryption \
        --bucket "$BUCKET_NAME" \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    # Block public access
    aws s3api put-public-access-block \
        --bucket "$BUCKET_NAME" \
        --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    
    log "S3 bucket $BUCKET_NAME created successfully"
fi

# Create DynamoDB table for state locking
log "Creating DynamoDB table: $DYNAMODB_TABLE"
if aws dynamodb describe-table --table-name "$DYNAMODB_TABLE" --region "$REGION" >/dev/null 2>&1; then
    warn "DynamoDB table $DYNAMODB_TABLE already exists"
else
    aws dynamodb create-table \
        --table-name "$DYNAMODB_TABLE" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$REGION"
    
    log "Waiting for DynamoDB table to become active..."
    aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE" --region "$REGION"
    
    log "DynamoDB table $DYNAMODB_TABLE created successfully"
fi

log "Terraform backend infrastructure setup completed!"
log "You can now initialize Terraform with the S3 backend."
log ""
log "Next steps:"
log "1. cd terraform"
log "2. terraform init"
log "3. Run ./deploy-staging.sh or ./deploy-production.sh" 