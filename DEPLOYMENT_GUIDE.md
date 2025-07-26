# Calndr Backend Deployment Guide

## Overview

This guide explains how to deploy the Calndr backend infrastructure and application to AWS using Terraform and GitHub Actions.

## Problem: Cluster Not Found Error

If you're seeing the error `ClusterNotFoundException: Cluster not found`, it means the ECS infrastructure hasn't been deployed yet. This guide will help you fix this issue.

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform installed** (version >= 1.0)
3. **GitHub repository** with proper secrets configured
4. **jq installed** (for JSON processing in scripts)

### Required AWS Permissions

Your AWS user/role needs permissions for:
- ECS (Elastic Container Service)
- ECR (Elastic Container Registry)
- RDS (Relational Database Service)
- ElastiCache (Redis)
- VPC and networking resources
- IAM roles and policies
- CloudWatch logs
- Application Load Balancer
- S3 (for Terraform state - optional but recommended)

## Step 1: Configure GitHub Secrets

Ensure these secrets are set in your GitHub repository settings:

```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

## Step 2: Set Up Terraform Backend

### Option A: Automatic Setup (Recommended)
The deployment scripts will automatically set up the S3 backend when you run them. No manual action needed.

### Option B: Manual Setup
If you prefer to set up the backend manually:

```bash
# Run the backend setup script
./terraform/setup-backend.sh
```

Or manually create the resources:

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://calndr-terraform-state --region us-east-1

# Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name calndr-terraform-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1
```

### Option C: Local Backend (Testing Only)
For testing without S3 backend, you can use local state:

```bash
cd terraform
# Backup the original main.tf
mv main.tf main-s3.tf
# Use the local backend version
mv main-local.tf main.tf
```

**Note: Local backend doesn't support team collaboration and state locking.**

## Step 3: Deploy Infrastructure

### Option A: Deploy Staging Environment

```bash
# Deploy staging infrastructure
./deploy-staging.sh
```

This will:
- Create the `calndr-staging-cluster` ECS cluster
- Set up VPC, subnets, and networking
- Create RDS PostgreSQL database
- Set up Redis cache
- Create ECR repository
- Configure load balancer and security groups

### Option B: Deploy Production Environment

```bash
# Deploy production infrastructure (requires extra confirmation)
./deploy-production.sh
```

This will:
- Create the `calndr-production-cluster` ECS cluster
- Set up production-sized infrastructure
- Enable deletion protection and enhanced backups

### Manual Deployment (Alternative)

If you prefer manual control:

```bash
cd terraform

# Initialize Terraform
terraform init

# For staging
terraform workspace new staging
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"

# For production
terraform workspace new production
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"
```

## Step 4: Verify Infrastructure

After deployment, verify the infrastructure exists:

```bash
# Check ECS clusters
aws ecs list-clusters --region us-east-1

# Check specific cluster
aws ecs describe-clusters --clusters calndr-staging-cluster --region us-east-1
aws ecs describe-clusters --clusters calndr-production-cluster --region us-east-1
```

## Step 5: Trigger Application Deployment

Once infrastructure is deployed:

### For Staging
Push to the `develop` branch:
```bash
git checkout develop
git push origin develop
```

### For Production
Push to the `main` branch:
```bash
git checkout main
git push origin main
```

## Environment Configuration

### Staging Environment
- **Cluster**: `calndr-staging-cluster`
- **Service**: `calndr-staging-service`
- **Domain**: `staging.calndr.club`
- **Size**: Smaller instances for cost efficiency
- **Backup**: 3-day retention
- **Deletion Protection**: Disabled

### Production Environment
- **Cluster**: `calndr-production-cluster`
- **Service**: `calndr-production-service`
- **Domain**: `calndr.club`
- **Size**: Production-ready instances
- **Backup**: 30-day retention
- **Deletion Protection**: Enabled

## Troubleshooting

### 1. GitHub Actions Still Failing

The updated GitHub Actions workflow now:
- Checks if clusters exist before attempting deployment
- Shows helpful warning messages if infrastructure isn't deployed
- Uses dynamic cluster names based on environment

### 2. Terraform Backend/State Issues

**DynamoDB Table Not Found Error:**
```bash
# If you see "ResourceNotFoundException" for DynamoDB table
./terraform/setup-backend.sh
```

**S3 Bucket Not Found Error:**
```bash
# Check if bucket exists
aws s3api head-bucket --bucket calndr-terraform-state

# If not, run setup script
./terraform/setup-backend.sh
```

**General State Issues:**
```bash
cd terraform

# List current state
terraform state list

# Import existing resources if needed
terraform import aws_ecs_cluster.main calndr-production-cluster

# If state is corrupted, you can start fresh (CAUTION: Will lose state history)
rm -rf .terraform
terraform init
```

### 3. AWS Credentials Issues

Ensure AWS credentials have sufficient permissions:

```bash
# Test AWS access
aws sts get-caller-identity

# Test ECS access
aws ecs list-clusters --region us-east-1
```

### 4. Cost Optimization

To minimize costs:
- Use staging environment for development
- Consider spot instances for non-production
- Monitor CloudWatch costs and set up billing alerts

## Infrastructure Costs

### Staging (Estimated Monthly)
- ECS Fargate: ~$30-50
- RDS t3.micro: ~$20
- ElastiCache t3.micro: ~$15
- Load Balancer: ~$20
- **Total: ~$85-105/month**

### Production (Estimated Monthly)
- ECS Fargate: ~$100-200
- RDS t3.small: ~$40
- ElastiCache t3.small: ~$30
- Load Balancer: ~$20
- **Total: ~$190-290/month**

*Costs may vary based on usage and AWS pricing changes.*

## Cleanup

To destroy infrastructure:

```bash
cd terraform

# For staging
terraform workspace select staging
terraform destroy -var-file="staging.tfvars"

# For production
terraform workspace select production
terraform destroy -var-file="production.tfvars"
```

## Next Steps

1. **Monitor Deployments**: Check AWS Console for deployment status
2. **Set Up DNS**: Point your domain to the load balancer
3. **Configure SSL**: Set up SSL certificates in ACM
4. **Set Up Monitoring**: Configure CloudWatch alarms and dashboards
5. **Test Thoroughly**: Verify all functionality works as expected

## Support

If you encounter issues:
1. Check CloudWatch logs for detailed error messages
2. Verify AWS permissions and resource limits
3. Review Terraform state and plan outputs
4. Check GitHub Actions logs for deployment details 