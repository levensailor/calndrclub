#!/bin/bash

# SSM Parameter Store Setup Script Template for Calndr
# ⚠️  IMPORTANT: This is a TEMPLATE file with placeholder values
# Copy this file and replace the placeholder values with your actual credentials before use

set -e

# Configuration
REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# ⚠️  REPLACE THESE WITH YOUR ACTUAL VALUES ⚠️
# These are placeholder values - you must update them with real credentials
SECRET_KEY="your_application_secret_key_here"
DB_PASSWORD="your_database_password_here"
AWS_ACCESS_KEY_ID="your_aws_access_key_id_here"
AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key_here"
GOOGLE_PLACES_API_KEY="your_google_places_api_key_here"
SNS_PLATFORM_APPLICATION_ARN="your_sns_platform_arn_here"
SMTP_USER="your_smtp_username_here"
SMTP_PASSWORD="your_smtp_password_here"
APPLE_PRIVATE_KEY="your_apple_private_key_here"

# Function to create or update SSM parameter
create_ssm_parameter() {
    local environment=$1
    local parameter_name=$2
    local parameter_value=$3
    local parameter_type=${4:-"SecureString"}
    local description=$5
    
    local full_parameter_name="/calndr/${environment}/${parameter_name}"
    
    # Check if parameter exists
    if aws ssm get-parameter --region "$REGION" --name "$full_parameter_name" >/dev/null 2>&1; then
        info "Updating existing parameter: $full_parameter_name"
        aws ssm put-parameter \
            --region "$REGION" \
            --name "$full_parameter_name" \
            --value "$parameter_value" \
            --type "$parameter_type" \
            --overwrite \
            --description "$description" >/dev/null
    else
        info "Creating new parameter: $full_parameter_name"
        aws ssm put-parameter \
            --region "$REGION" \
            --name "$full_parameter_name" \
            --value "$parameter_value" \
            --type "$parameter_type" \
            --description "$description" >/dev/null
    fi
    
    success "Parameter $parameter_name created/updated for $environment"
}

# Function to check if placeholder values are still present
check_placeholder_values() {
    local has_placeholders=false
    
    if [[ "$SECRET_KEY" == "your_application_secret_key_here" ]]; then
        error "SECRET_KEY still has placeholder value - please update with actual secret"
        has_placeholders=true
    fi
    
    if [[ "$DB_PASSWORD" == "your_database_password_here" ]]; then
        error "DB_PASSWORD still has placeholder value - please update with actual password"
        has_placeholders=true
    fi
    
    if [[ "$AWS_ACCESS_KEY_ID" == "your_aws_access_key_id_here" ]]; then
        error "AWS_ACCESS_KEY_ID still has placeholder value - please update with actual key"
        has_placeholders=true
    fi
    
    if [[ "$AWS_SECRET_ACCESS_KEY" == "your_aws_secret_access_key_here" ]]; then
        error "AWS_SECRET_ACCESS_KEY still has placeholder value - please update with actual secret"
        has_placeholders=true
    fi
    
    if [[ "$GOOGLE_PLACES_API_KEY" == "your_google_places_api_key_here" ]]; then
        error "GOOGLE_PLACES_API_KEY still has placeholder value - please update with actual key"
        has_placeholders=true
    fi
    
    if [[ "$SNS_PLATFORM_APPLICATION_ARN" == "your_sns_platform_arn_here" ]]; then
        error "SNS_PLATFORM_APPLICATION_ARN still has placeholder value - please update with actual ARN"
        has_placeholders=true
    fi
    
    if [[ "$SMTP_USER" == "your_smtp_username_here" ]]; then
        error "SMTP_USER still has placeholder value - please update with actual username"
        has_placeholders=true
    fi
    
    if [[ "$SMTP_PASSWORD" == "your_smtp_password_here" ]]; then
        error "SMTP_PASSWORD still has placeholder value - please update with actual password"
        has_placeholders=true
    fi
    
    if [[ "$APPLE_PRIVATE_KEY" == "your_apple_private_key_here" ]]; then
        error "APPLE_PRIVATE_KEY still has placeholder value - please update with actual private key"
        has_placeholders=true
    fi
    
    if [ "$has_placeholders" = true ]; then
        error "This script still contains placeholder values!"
        error "Please edit the script and replace all placeholder values with actual credentials before running."
        exit 1
    fi
}

# Function to setup parameters for an environment
setup_environment_parameters() {
    local environment=$1
    
    # Check for placeholder values before proceeding
    check_placeholder_values
    
    log "Setting up SSM parameters for ${environment} environment..."
    echo
    
    # Core application secrets
    create_ssm_parameter "$environment" "secret_key" "$SECRET_KEY" "SecureString" "Application secret key for JWT tokens"
    
    # Database credentials
    create_ssm_parameter "$environment" "db_user" "postgres" "SecureString" "Database username"
    create_ssm_parameter "$environment" "db_password" "$DB_PASSWORD" "SecureString" "Database password"
    
    # AWS credentials
    create_ssm_parameter "$environment" "aws_access_key_id" "$AWS_ACCESS_KEY_ID" "SecureString" "AWS Access Key ID"
    create_ssm_parameter "$environment" "aws_secret_access_key" "$AWS_SECRET_ACCESS_KEY" "SecureString" "AWS Secret Access Key"
    
    # Google Places API
    create_ssm_parameter "$environment" "google_places_api_key" "$GOOGLE_PLACES_API_KEY" "SecureString" "Google Places API key"
    
    # SNS Platform Application ARN
    create_ssm_parameter "$environment" "sns_platform_application_arn" "$SNS_PLATFORM_APPLICATION_ARN" "SecureString" "SNS Platform Application ARN for push notifications"
    
    # SMTP credentials
    create_ssm_parameter "$environment" "smtp_user" "$SMTP_USER" "SecureString" "SMTP username for email sending"
    create_ssm_parameter "$environment" "smtp_password" "$SMTP_PASSWORD" "SecureString" "SMTP password for email sending"
    
    # Apple Sign-In private key
    create_ssm_parameter "$environment" "apple_private_key" "$APPLE_PRIVATE_KEY" "SecureString" "Apple Sign-In private key"
    
    # Google Client Secret (placeholder - update with actual value when available)
    create_ssm_parameter "$environment" "google_client_secret" "" "SecureString" "Google OAuth client secret"
    
    # Redis password (if production environment and Redis auth is enabled)
    if [ "$environment" == "production" ]; then
        # This would be generated by Terraform for ElastiCache with auth enabled
        warning "Redis password for production should be set up via Terraform ElastiCache configuration"
    else
        # For staging, if Redis auth is not enabled, use empty password
        create_ssm_parameter "$environment" "redis_password" "" "SecureString" "Redis password for staging"
    fi
    
    echo
    success "All SSM parameters set up for $environment environment!"
}

# Function to list existing parameters
list_parameters() {
    local environment=$1
    
    log "Listing SSM parameters for ${environment} environment..."
    echo
    
    local parameters=$(aws ssm get-parameters-by-path \
        --region "$REGION" \
        --path "/calndr/${environment}/" \
        --recursive \
        --query 'Parameters[*].Name' \
        --output text)
    
    if [ -z "$parameters" ]; then
        warning "No parameters found for $environment environment"
    else
        info "Found parameters:"
        for param in $parameters; do
            echo "  $param"
        done
    fi
}

# Function to delete all parameters for an environment
delete_environment_parameters() {
    local environment=$1
    
    warning "This will DELETE ALL SSM parameters for $environment environment!"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Operation cancelled"
        return 0
    fi
    
    log "Deleting SSM parameters for ${environment} environment..."
    
    local parameters=$(aws ssm get-parameters-by-path \
        --region "$REGION" \
        --path "/calndr/${environment}/" \
        --recursive \
        --query 'Parameters[*].Name' \
        --output text)
    
    if [ -z "$parameters" ]; then
        info "No parameters found to delete"
        return 0
    fi
    
    for param in $parameters; do
        info "Deleting parameter: $param"
        aws ssm delete-parameter --region "$REGION" --name "$param" >/dev/null
        success "Deleted $param"
    done
    
    success "All parameters deleted for $environment environment"
}

# Function to show usage
show_usage() {
    echo -e "${PURPLE}Calndr SSM Parameter Store Setup (TEMPLATE)${NC}"
    echo
    warning "THIS IS A TEMPLATE FILE WITH PLACEHOLDER VALUES!"
    warning "You MUST edit this file and replace all placeholder values before use."
    echo
    echo "Usage: $0 [command] [environment]"
    echo
    echo "Commands:"
    echo "  setup <env>     - Set up all SSM parameters for environment"
    echo "  list <env>      - List existing parameters for environment"
    echo "  delete <env>    - Delete all parameters for environment"
    echo "  setup-all       - Set up parameters for both staging and production"
    echo "  list-all        - List parameters for both environments"
    echo
    echo "Environments: staging, production"
    echo
    echo "Examples:"
    echo "  $0 setup staging        # Set up staging parameters"
    echo "  $0 setup production     # Set up production parameters"
    echo "  $0 setup-all            # Set up both environments"
    echo "  $0 list staging         # List staging parameters"
    echo "  $0 delete staging       # Delete staging parameters"
    echo
    echo "⚠️  IMPORTANT SECURITY NOTES:"
    echo "   - This is a TEMPLATE file - replace placeholder values with real credentials"
    echo "   - Only run with authorized personnel"
    echo "   - Delete this file after use if it contains actual credentials"
    echo "   - Never commit actual credentials to version control"
}

# Main script logic
main() {
    local command=$1
    local environment=$2
    
    case $command in
        "setup")
            if [ -z "$environment" ]; then
                error "Environment is required for setup command"
                show_usage
                exit 1
            fi
            setup_environment_parameters "$environment"
            ;;
        "list")
            if [ -z "$environment" ]; then
                error "Environment is required for list command"
                show_usage
                exit 1
            fi
            list_parameters "$environment"
            ;;
        "delete")
            if [ -z "$environment" ]; then
                error "Environment is required for delete command"
                show_usage
                exit 1
            fi
            delete_environment_parameters "$environment"
            ;;
        "setup-all")
            setup_environment_parameters "staging"
            echo
            setup_environment_parameters "production"
            ;;
        "list-all")
            list_parameters "staging"
            echo
            list_parameters "production"
            ;;
        *)
            show_usage
            ;;
    esac
}

# Check if AWS CLI is available and configured
if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! aws sts get-caller-identity > /dev/null 2>&1; then
    error "AWS CLI is not configured. Please run 'aws configure'."
    exit 1
fi

# Show warning about template nature
warning "THIS IS A TEMPLATE FILE WITH PLACEHOLDER VALUES!"
warning "Please copy this file and replace placeholder values with actual credentials."
warning "Make sure you're authorized to set up these parameters."
echo

# Run main function
main "$@" 