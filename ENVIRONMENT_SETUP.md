# Environment Variables Setup Guide

This document explains how to set up environment variables for the Calndr application using AWS SSM Parameter Store for secure secret management.

## 🔐 Security Model

All sensitive data (passwords, API keys, secrets) are stored in **AWS SSM Parameter Store** as SecureString parameters, not in terraform files or environment variables. This ensures:

- ✅ Secrets are encrypted at rest
- ✅ Access is controlled by IAM policies  
- ✅ Audit trail of secret access
- ✅ No secrets in version control
- ✅ GitHub secret scanning protection

## 📋 Required Environment Variables

### Database Configuration
- `DB_USER` = postgres
- `DB_PASSWORD` = [Your database password]
- `DB_NAME` = postgres  
- `DB_HOST` = [Your RDS endpoint] (managed by Terraform)
- `DB_PORT` = 5432

### Application Security
- `SECRET_KEY` = [Your application secret key]
- `AWS_ACCESS_KEY_ID` = [Your AWS access key ID]
- `AWS_SECRET_ACCESS_KEY` = [Your AWS secret access key]
- `AWS_REGION` = us-east-1
- `AWS_S3_BUCKET_NAME` = calndr-profile

### Apple Sign-In & APNS Configuration
- `APPLE_CLIENT_ID` = club.calndr
- `APPLE_TEAM_ID` = HU4EE3MB4T
- `APPLE_KEY_ID` = 9Q9D25269Q
- `APPLE_PRIVATE_KEY` = [Private key content]
- `APPLE_REDIRECT_URI` = https://calndr.club/api/v1/auth/apple/callback
- `APNS_CERT_PATH` = /var/www/cal-app/AuthKey_RZ6KL226Z5.p8
- `APNS_KEY_ID` = 9Q9D25269Q (same as APPLE_KEY_ID)
- `APNS_TEAM_ID` = HU4EE3MB4T (same as APPLE_TEAM_ID)
- `APNS_TOPIC` = club.calndr

### Google Services
- `GOOGLE_CLIENT_ID` = [Your Google OAuth client ID]
- `GOOGLE_PLACES_API_KEY` = [Your Google Places API key]
- `GOOGLE_CLIENT_SECRET` = [Your Google OAuth client secret]

### Email/SMTP Configuration
- `SMTP_HOST` = email-smtp.us-east-1.amazonaws.com
- `SMTP_PORT` = 25
- `SMTP_USER` = [Your SMTP username]
- `SMTP_PASSWORD` = [Your SMTP password]

### Push Notifications
- `SNS_PLATFORM_APPLICATION_ARN` = [Your SNS platform application ARN]

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Copy template and configure with your credentials
cp scripts/setup-ssm-parameters-template.sh scripts/setup-ssm-parameters.sh
# Edit the script and replace placeholder values with actual credentials
# Then run:
./scripts/setup-ssm-parameters.sh setup-all

# Or set up specific environment
./scripts/setup-ssm-parameters.sh setup staging
./scripts/setup-ssm-parameters.sh setup production
```

### Option 2: Manual Setup
```bash
# Create parameters manually for production
 aws ssm put-parameter \
     --region us-east-1 \
     --name "/calndr/production/secret_key" \
     --value "your_secret_key_here" \
     --type "SecureString" \
     --description "Application secret key"

# Repeat for all other parameters...
```

## 📊 Verification

### Check SSM Parameters
```bash
# List all parameters for environment (using template for listing only)
./scripts/setup-ssm-parameters-template.sh list production
./scripts/setup-ssm-parameters-template.sh list staging

# Verify ECS task definition has all variables
./scripts/verify-env-vars.sh all production
./scripts/verify-env-vars.sh all staging
```

### Check Live ECS Configuration
```bash
# View current environment variables in running ECS tasks
./scripts/verify-env-vars.sh check production
./scripts/verify-env-vars.sh check staging
```

## 🏗️ How It Works

### 1. Terraform Configuration
- **terraform/ecs.tf**: ECS task definition references SSM parameters as secrets
- **terraform/*.tfvars**: Contains non-sensitive configuration only
- **terraform/main.tf**: Creates SSM parameter resources

### 2. SSM Parameter Store Structure
```
/calndr/production/
├── secret_key
├── db_password
├── aws_access_key_id
├── aws_secret_access_key
├── google_places_api_key
├── sns_platform_application_arn
├── smtp_user
├── smtp_password
├── apple_private_key
└── google_client_secret

/calndr/staging/
├── [same structure as production]
└── ...
```

### 3. ECS Task Definition
The ECS task definition in `terraform/ecs.tf` has two types of configuration:

**Environment Variables** (non-sensitive):
```hcl
environment = [
  {
    name  = "APPLE_CLIENT_ID"
    value = var.apple_client_id
  },
  {
    name  = "SMTP_HOST"
    value = var.smtp_host
  }
  # ... more non-sensitive vars
]
```

**Secrets** (sensitive data from SSM):
```hcl
secrets = [
  {
    name      = "SECRET_KEY"
    valueFrom = aws_ssm_parameter.secret_key.arn
  },
  {
    name      = "DB_PASSWORD"
    valueFrom = aws_ssm_parameter.db_password.arn
  }
  # ... more sensitive vars
]
```

## 🔧 Environment-Specific Differences

### Production vs Staging
- **Domain URLs**: Different redirect URIs for Apple/Google OAuth
- **Database**: Different RDS instances
- **Redis**: Production has auth enabled, staging might not
- **Resource sizing**: Production has larger instances
- **Backup retention**: Production has longer retention periods

### Configuration Updates
When updating environment variables:

1. **Non-sensitive data**: Update `terraform/*.tfvars` files
2. **Sensitive data**: Update SSM Parameter Store using the script
3. **Deploy**: Run `terraform apply` to update ECS task definition
4. **Restart**: ECS will automatically restart tasks with new configuration

## 🚨 Security Best Practices

### Access Control
- Limit SSM parameter access to authorized personnel only
- Use IAM policies to restrict parameter access by environment
- Enable CloudTrail to audit parameter access

### Secret Rotation
- Regularly rotate sensitive credentials
- Update SSM parameters first, then restart ECS tasks
- Monitor application logs for authentication failures

### Development
- Never put secrets in code or configuration files
- Use environment-specific SSM parameters
- Test with non-production data when possible

## 🛠️ Troubleshooting

### Common Issues

**1. ECS Task Won't Start**
```bash
# Check ECS service events
aws ecs describe-services --cluster calndr-production-cluster --services calndr-production-service

# Check task definition can access SSM parameters
./scripts/verify-env-vars.sh check production
```

**2. SSM Parameter Not Found**
```bash
# List all parameters
./scripts/setup-ssm-parameters.sh list production

# Create missing parameter
aws ssm put-parameter --name "/calndr/production/missing_param" --value "value" --type "SecureString"
```

**3. Permission Denied**
```bash
# Check IAM permissions for ECS task role
aws iam get-role-policy --role-name calndr-production-ecs-task-role --policy-name ssm-access
```

### Useful Commands

```bash
# View all SSM parameters
aws ssm get-parameters-by-path --path "/calndr/" --recursive

# Get specific parameter value (for debugging)
aws ssm get-parameter --name "/calndr/production/secret_key" --with-decryption

# Update parameter
aws ssm put-parameter --name "/calndr/production/secret_key" --value "new_value" --overwrite

# Delete parameter
aws ssm delete-parameter --name "/calndr/production/old_param"
```

## 📝 Maintenance

### Regular Tasks
- [ ] Review and rotate AWS access keys quarterly
- [ ] Update API keys when they expire
- [ ] Monitor SSM parameter access in CloudTrail
- [ ] Verify all parameters are properly encrypted
- [ ] Test disaster recovery with parameter backup/restore

### Deployment Checklist
- [ ] All required SSM parameters exist
- [ ] ECS task definition references correct parameters
- [ ] IAM roles have necessary SSM permissions
- [ ] Environment-specific values are correct
- [ ] Application starts successfully with new configuration

---

**⚠️ Important**: This configuration contains sensitive production data. Handle with appropriate security measures and limit access to authorized personnel only. 