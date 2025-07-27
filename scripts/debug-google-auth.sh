#!/bin/bash

# Google OAuth Debug Script for Calndr
# Test Google authentication endpoints and troubleshoot issues

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

# Function to check Google OAuth configuration
check_google_config() {
    local environment=$1
    
    log "Checking Google OAuth configuration for ${environment}..."
    echo
    
    # Check SSM parameters
    local google_client_id=$(aws ssm get-parameter \
        --region "$REGION" \
        --name "/calndr/${environment}/google_client_id" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "NOT_FOUND")
    
    local google_client_secret=$(aws ssm get-parameter \
        --region "$REGION" \
        --name "/calndr/${environment}/google_client_secret" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "NOT_FOUND")
    
    info "Google Client ID: ${google_client_id}"
    
    if [ "$google_client_secret" == "NOT_FOUND" ]; then
        error "Google Client Secret not found in SSM"
    elif [ -z "$google_client_secret" ] || [ "$google_client_secret" == "" ]; then
        error "Google Client Secret is empty"
    else
        success "Google Client Secret is configured (length: ${#google_client_secret})"
    fi
    
    # Check if the client ID is valid format
    if [[ "$google_client_id" =~ ^[0-9]+-[a-zA-Z0-9]+\.apps\.googleusercontent\.com$ ]]; then
        success "Google Client ID format is valid"
    else
        error "Google Client ID format is invalid"
    fi
}

# Function to test Google OAuth endpoints
test_google_endpoints() {
    local base_url=$1
    local environment=$2
    
    log "Testing Google OAuth endpoints for ${environment} at ${base_url}..."
    echo
    
    # Test Google login URL endpoint
    info "Testing /auth/google/login endpoint..."
    local response=$(curl -s -w "\n%{http_code}" "${base_url}/api/v1/auth/google/login" 2>/dev/null)
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" == "200" ]; then
        success "Google login endpoint is working"
        echo "Response: $body"
    else
        error "Google login endpoint failed with status: $status_code"
        echo "Response: $body"
    fi
    
    echo
    info "Note: To test /google/callback or /google/ios-login, you need a valid Google ID token"
    info "These endpoints require actual authentication with Google"
}

# Function to check ECS task environment variables
check_ecs_google_vars() {
    local environment=$1
    
    log "Checking Google environment variables in ECS for ${environment}..."
    echo
    
    local cluster_name="calndr-${environment}-cluster"
    local service_name="calndr-${environment}-service"
    
    # Get the current task definition
    local task_def_arn=$(aws ecs describe-services \
        --region "$REGION" \
        --cluster "$cluster_name" \
        --services "$service_name" \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null)
    
    if [ "$task_def_arn" == "None" ] || [ -z "$task_def_arn" ]; then
        warning "No active ECS service found for ${environment}"
        return 1
    fi
    
    info "Task Definition: ${task_def_arn##*/}"
    
    # Get task definition details and check Google-related variables
    local task_def_json=$(aws ecs describe-task-definition \
        --region "$REGION" \
        --task-definition "$task_def_arn" \
        --query 'taskDefinition.containerDefinitions[0]' 2>/dev/null)
    
    # Check environment variables
    local google_client_id=$(echo "$task_def_json" | jq -r '.environment[]? | select(.name=="GOOGLE_CLIENT_ID") | .value')
    local google_redirect_uri=$(echo "$task_def_json" | jq -r '.environment[]? | select(.name=="GOOGLE_REDIRECT_URI") | .value')
    
    # Check secrets
    local google_client_secret_param=$(echo "$task_def_json" | jq -r '.secrets[]? | select(.name=="GOOGLE_CLIENT_SECRET") | .valueFrom')
    
    info "Google Configuration in ECS:"
    echo "  GOOGLE_CLIENT_ID: $google_client_id"
    echo "  GOOGLE_REDIRECT_URI: $google_redirect_uri"
    echo "  GOOGLE_CLIENT_SECRET (SSM): $google_client_secret_param"
    
    if [ "$google_client_id" != "null" ] && [ -n "$google_client_id" ]; then
        success "GOOGLE_CLIENT_ID is configured in ECS"
    else
        error "GOOGLE_CLIENT_ID is missing in ECS task definition"
    fi
    
    if [ "$google_client_secret_param" != "null" ] && [ -n "$google_client_secret_param" ]; then
        success "GOOGLE_CLIENT_SECRET is configured in ECS"
    else
        error "GOOGLE_CLIENT_SECRET is missing in ECS task definition"
    fi
}

# Function to show Google OAuth troubleshooting steps
show_troubleshooting() {
    log "Google OAuth Troubleshooting Steps:"
    echo
    
    info "1. Verify Google Client Secret:"
    echo "   - Get your Google Client Secret from Google Cloud Console"
    echo "   - Update scripts/setup-ssm-parameters.sh with the actual secret"
    echo "   - Run: ./scripts/setup-ssm-parameters.sh setup production"
    echo
    
    info "2. Check Google Cloud Console Configuration:"
    echo "   - Ensure redirect URIs are configured correctly"
    echo "   - For production: https://calndr.club/api/v1/auth/google/callback"
    echo "   - For staging: https://staging.calndr.club/api/v1/auth/google/callback"
    echo
    
    info "3. Verify iOS App Configuration:"
    echo "   - Ensure iOS app is using the correct Google Client ID"
    echo "   - Check that the app is sending requests to the correct endpoint"
    echo "   - Verify the ID token is being sent in the correct format"
    echo
    
    info "4. Check Backend Logs:"
    echo "   - Use: ./scripts/quick-logs.sh errors-prod"
    echo "   - Look for Google authentication errors"
    echo "   - Check for missing environment variables"
    echo
    
    info "5. Test Endpoints:"
    echo "   - Production: $0 test https://calndr.club production"
    echo "   - Staging: $0 test https://staging.calndr.club staging"
}

# Function to show usage
show_usage() {
    echo -e "${PURPLE}Calndr Google OAuth Debug Tool${NC}"
    echo
    echo "Usage: $0 [command] [environment/url] [environment]"
    echo
    echo "Commands:"
    echo "  config <env>          - Check Google OAuth configuration"
    echo "  ecs <env>             - Check ECS environment variables"
    echo "  test <url> <env>      - Test Google OAuth endpoints"
    echo "  troubleshoot          - Show troubleshooting steps"
    echo "  all <env>             - Run all checks for environment"
    echo
    echo "Environments: staging, production"
    echo
    echo "Examples:"
    echo "  $0 config production                                    # Check production config"
    echo "  $0 ecs staging                                          # Check staging ECS vars"
    echo "  $0 test https://calndr.club production                  # Test production endpoints"
    echo "  $0 troubleshoot                                         # Show troubleshooting guide"
    echo "  $0 all production                                       # Run all checks"
}

# Main script logic
main() {
    local command=$1
    local param1=$2
    local param2=$3
    
    case $command in
        "config")
            if [ -z "$param1" ]; then
                error "Environment is required for config command"
                show_usage
                exit 1
            fi
            check_google_config "$param1"
            ;;
        "ecs")
            if [ -z "$param1" ]; then
                error "Environment is required for ecs command"
                show_usage
                exit 1
            fi
            check_ecs_google_vars "$param1"
            ;;
        "test")
            if [ -z "$param1" ] || [ -z "$param2" ]; then
                error "URL and environment are required for test command"
                show_usage
                exit 1
            fi
            test_google_endpoints "$param1" "$param2"
            ;;
        "troubleshoot")
            show_troubleshooting
            ;;
        "all")
            if [ -z "$param1" ]; then
                error "Environment is required for all command"
                show_usage
                exit 1
            fi
            check_google_config "$param1"
            echo
            check_ecs_google_vars "$param1"
            echo
            show_troubleshooting
            ;;
        *)
            show_usage
            ;;
    esac
}

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    error "jq is not installed. Please install it first (brew install jq)."
    exit 1
fi

# Run main function
main "$@" 