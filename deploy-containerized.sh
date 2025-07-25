#!/bin/bash
set -e

# Containerized Deployment Script for Calndr Backend
# This script helps deploy the containerized infrastructure

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT=""
AWS_REGION="us-east-1"
PROJECT_NAME="calndr"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S EST')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print usage
usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

COMMANDS:
    init-infrastructure    Initialize Terraform infrastructure
    deploy-staging        Deploy to staging environment
    deploy-production     Deploy to production environment
    build-local           Build Docker image locally
    push-image           Push Docker image to ECR
    update-service       Update ECS service
    rollback             Rollback to previous deployment
    logs                 View application logs
    status               Check deployment status
    cleanup              Clean up old resources
    help                 Show this help message

OPTIONS:
    -e, --environment    Environment (staging|production)
    -r, --region         AWS region (default: us-east-1)
    -v, --verbose        Enable verbose output
    -h, --help           Show this help message

EXAMPLES:
    $0 init-infrastructure -e staging
    $0 deploy-staging
    $0 deploy-production
    $0 logs -e production
    $0 status -e staging

PREREQUISITES:
    - AWS CLI configured
    - Docker installed
    - Terraform installed
    - GitHub secrets configured for CI/CD

EOF
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    success "All prerequisites are met."
}

# Function to initialize Terraform infrastructure
init_infrastructure() {
    local env=$1
    
    if [[ -z "$env" ]]; then
        error "Environment not specified. Use -e staging or -e production"
        exit 1
    fi
    
    log "Initializing Terraform infrastructure for $env environment..."
    
    cd "$SCRIPT_DIR/terraform"
    
    # Create terraform.tfvars file if it doesn't exist
    if [[ ! -f "terraform.tfvars" ]]; then
        cat > terraform.tfvars << EOF
# Terraform Variables for $env environment
environment = "$env"
project_name = "$PROJECT_NAME"
aws_region = "$AWS_REGION"

# These will be prompted for or set via environment variables
# secret_key = "your-secret-key"
# aws_access_key_id = "your-aws-access-key"
# aws_secret_access_key = "your-aws-secret-key"

# Optional configurations
# google_places_api_key = "your-google-places-api-key"
# apple_client_id = "your-apple-client-id"
# google_client_id = "your-google-client-id"
# google_client_secret = "your-google-client-secret"
EOF
        warning "Created terraform.tfvars template. Please fill in the required variables."
    fi
    
    # Initialize Terraform
    terraform init
    
    # Plan the infrastructure
    terraform plan -var="environment=$env"
    
    echo
    warning "Review the Terraform plan above carefully."
    read -p "Do you want to apply these changes? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -var="environment=$env"
        success "Infrastructure initialized successfully for $env environment."
    else
        log "Infrastructure initialization cancelled."
    fi
    
    cd "$SCRIPT_DIR"
}

# Function to build Docker image locally
build_local() {
    log "Building Docker image locally..."
    
    # Check if Dockerfile exists
    if [[ ! -f "$SCRIPT_DIR/Dockerfile" ]]; then
        error "Dockerfile not found in $SCRIPT_DIR"
        exit 1
    fi
    
    # Build the image
    local image_tag="${PROJECT_NAME}-backend:latest"
    docker build -t "$image_tag" "$SCRIPT_DIR"
    
    success "Docker image built successfully: $image_tag"
    
    # Test the image
    log "Testing the Docker image..."
    docker run --rm -d --name "${PROJECT_NAME}-test" -p 8001:8000 "$image_tag" > /dev/null
    
    sleep 5
    
    if curl -f http://localhost:8001/health &> /dev/null; then
        success "Docker image test passed."
        docker stop "${PROJECT_NAME}-test" > /dev/null
    else
        error "Docker image test failed."
        docker stop "${PROJECT_NAME}-test" > /dev/null || true
        exit 1
    fi
}

# Function to push image to ECR
push_image() {
    local env=$1
    
    if [[ -z "$env" ]]; then
        error "Environment not specified. Use -e staging or -e production"
        exit 1
    fi
    
    log "Pushing Docker image to ECR for $env environment..."
    
    # Get ECR login token
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # Get ECR repository URI
    local repository_uri=$(aws ecr describe-repositories --repository-names "${PROJECT_NAME}-backend" --region "$AWS_REGION" --query 'repositories[0].repositoryUri' --output text)
    
    # Tag and push the image
    local image_tag="$(git rev-parse HEAD)"
    docker tag "${PROJECT_NAME}-backend:latest" "$repository_uri:$image_tag"
    docker tag "${PROJECT_NAME}-backend:latest" "$repository_uri:$env-latest"
    
    docker push "$repository_uri:$image_tag"
    docker push "$repository_uri:$env-latest"
    
    success "Docker image pushed successfully to ECR."
}

# Function to view logs
view_logs() {
    local env=$1
    
    if [[ -z "$env" ]]; then
        error "Environment not specified. Use -e staging or -e production"
        exit 1
    fi
    
    log "Viewing logs for $env environment..."
    
    # Get the log group name
    local log_group="/ecs/${PROJECT_NAME}-${env}"
    
    # Stream logs
    aws logs tail "$log_group" --follow --region "$AWS_REGION"
}

# Function to check deployment status
check_status() {
    local env=$1
    
    if [[ -z "$env" ]]; then
        error "Environment not specified. Use -e staging or -e production"
        exit 1
    fi
    
    log "Checking deployment status for $env environment..."
    
    # Check ECS service status
    local cluster_name="${PROJECT_NAME}-${env}-cluster"
    local service_name="${PROJECT_NAME}-${env}-service"
    
    aws ecs describe-services \
        --cluster "$cluster_name" \
        --services "$service_name" \
        --region "$AWS_REGION" \
        --query 'services[0].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount,PendingCount:pendingCount}' \
        --output table
    
    # Check application health
    local domain
    if [[ "$env" == "production" ]]; then
        domain="https://calndr.club"
    else
        domain="https://${env}.calndr.club"
    fi
    
    log "Checking application health at $domain/health..."
    if curl -f "$domain/health" &> /dev/null; then
        success "Application is healthy."
    else
        error "Application health check failed."
    fi
}

# Function to cleanup old resources
cleanup() {
    local env=$1
    
    if [[ -z "$env" ]]; then
        error "Environment not specified. Use -e staging or -e production"
        exit 1
    fi
    
    log "Cleaning up old resources for $env environment..."
    
    # Clean up old ECR images
    local repository_name="${PROJECT_NAME}-backend"
    
    log "Cleaning up old ECR images..."
    aws ecr list-images \
        --repository-name "$repository_name" \
        --filter tagStatus=UNTAGGED \
        --query 'imageIds[?imageDigest!=null]|[10:]' \
        --output json \
        --region "$AWS_REGION" | \
    jq -r '.[] | @base64' | \
    while read -r img; do
        echo "$img" | base64 -d | jq -r '{imageDigest}'
    done | \
    xargs -r aws ecr batch-delete-image \
        --repository-name "$repository_name" \
        --image-ids file:///dev/stdin \
        --region "$AWS_REGION" || echo "No old images to delete"
    
    success "Cleanup completed."
}

# Main script logic
main() {
    local command=""
    local environment=""
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            init-infrastructure|deploy-staging|deploy-production|build-local|push-image|update-service|rollback|logs|status|cleanup|help)
                command=$1
                shift
                ;;
            -e|--environment)
                environment="$2"
                shift 2
                ;;
            -r|--region)
                AWS_REGION="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Set verbose mode
    if [[ "$verbose" == true ]]; then
        set -x
    fi
    
    # Handle commands
    case $command in
        init-infrastructure)
            check_prerequisites
            init_infrastructure "$environment"
            ;;
        deploy-staging)
            check_prerequisites
            environment="staging"
            build_local
            push_image "$environment"
            success "Staging deployment triggered. Check GitHub Actions for progress."
            ;;
        deploy-production)
            check_prerequisites
            environment="production"
            build_local
            push_image "$environment"
            success "Production deployment triggered. Check GitHub Actions for progress."
            ;;
        build-local)
            check_prerequisites
            build_local
            ;;
        push-image)
            check_prerequisites
            push_image "$environment"
            ;;
        logs)
            view_logs "$environment"
            ;;
        status)
            check_status "$environment"
            ;;
        cleanup)
            cleanup "$environment"
            ;;
        help|"")
            usage
            ;;
        *)
            error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 