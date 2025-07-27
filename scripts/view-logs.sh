#!/bin/bash

# Calndr ECS Log Viewer
# Easy access to application logs from ECS deployments

set -e

# Configuration
PROJECT_NAME="calndr"
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

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] $1${NC}"
}

# Check if AWS CLI is installed and configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        error "AWS CLI is not configured. Please run 'aws configure'."
        exit 1
    fi
}

# Function to list available environments
list_environments() {
    log "Available environments:"
    for env in staging production; do
        echo -e "  ${PURPLE}$env${NC}"
    done
}

# Function to stream live logs (like tail -f)
stream_logs() {
    local environment=$1
    local lines=${2:-100}
    
    local log_group="/ecs/${PROJECT_NAME}-${environment}"
    
    log "Streaming live logs from ${environment} environment..."
    info "Log group: ${log_group}"
    info "Press Ctrl+C to stop streaming"
    echo
    
    # Use CloudWatch Logs tail feature (requires AWS CLI v2)
    aws logs tail "$log_group" \
        --region "$REGION" \
        --follow \
        --since 1h \
        --format short
}

# Function to get recent logs
get_recent_logs() {
    local environment=$1
    local lines=${2:-100}
    local hours=${3:-1}
    
    local log_group="/ecs/${PROJECT_NAME}-${environment}"
    
    log "Getting last ${lines} log entries from ${environment} (last ${hours} hours)..."
    info "Log group: ${log_group}"
    echo
    
    # Get logs from the last specified hours
    local start_time=$(date -d "${hours} hours ago" +%s)000
    
    aws logs filter-log-events \
        --region "$REGION" \
        --log-group-name "$log_group" \
        --start-time "$start_time" \
        --max-items "$lines" \
        --query 'events[*].[timestamp,message]' \
        --output text | \
    while IFS=$'\t' read -r timestamp message; do
        # Convert timestamp to readable format
        local readable_time=$(date -d "@$(($timestamp/1000))" +'%Y-%m-%d %I:%M:%S %p EST')
        echo -e "${BLUE}[$readable_time]${NC} $message"
    done
}

# Function to search logs for errors
search_errors() {
    local environment=$1
    local hours=${2:-24}
    
    local log_group="/ecs/${PROJECT_NAME}-${environment}"
    
    log "Searching for errors in ${environment} (last ${hours} hours)..."
    info "Log group: ${log_group}"
    echo
    
    local start_time=$(date -d "${hours} hours ago" +%s)000
    
    aws logs filter-log-events \
        --region "$REGION" \
        --log-group-name "$log_group" \
        --start-time "$start_time" \
        --filter-pattern "ERROR" \
        --query 'events[*].[timestamp,message]' \
        --output text | \
    while IFS=$'\t' read -r timestamp message; do
        local readable_time=$(date -d "@$(($timestamp/1000))" +'%Y-%m-%d %I:%M:%S %p EST')
        echo -e "${RED}[$readable_time] $message${NC}"
    done
}

# Function to search logs with custom pattern
search_logs() {
    local environment=$1
    local pattern=$2
    local hours=${3:-24}
    
    local log_group="/ecs/${PROJECT_NAME}-${environment}"
    
    log "Searching for pattern '${pattern}' in ${environment} (last ${hours} hours)..."
    info "Log group: ${log_group}"
    echo
    
    local start_time=$(date -d "${hours} hours ago" +%s)000
    
    aws logs filter-log-events \
        --region "$REGION" \
        --log-group-name "$log_group" \
        --start-time "$start_time" \
        --filter-pattern "$pattern" \
        --query 'events[*].[timestamp,message]' \
        --output text | \
    while IFS=$'\t' read -r timestamp message; do
        local readable_time=$(date -d "@$(($timestamp/1000))" +'%Y-%m-%d %I:%M:%S %p EST')
        echo -e "${PURPLE}[$readable_time]${NC} $message"
    done
}

# Function to get service status
get_service_status() {
    local environment=$1
    
    local cluster_name="${PROJECT_NAME}-${environment}-cluster"
    local service_name="${PROJECT_NAME}-${environment}-service"
    
    log "Getting ECS service status for ${environment}..."
    echo
    
    aws ecs describe-services \
        --region "$REGION" \
        --cluster "$cluster_name" \
        --services "$service_name" \
        --query 'services[0].{
            ServiceName: serviceName,
            Status: status,
            RunningCount: runningCount,
            PendingCount: pendingCount,
            DesiredCount: desiredCount,
            TaskDefinition: taskDefinition,
            PlatformVersion: platformVersion
        }' \
        --output table
}

# Function to get task logs (latest task)
get_task_logs() {
    local environment=$1
    local lines=${2:-50}
    
    local cluster_name="${PROJECT_NAME}-${environment}-cluster"
    local service_name="${PROJECT_NAME}-${environment}-service"
    
    log "Getting logs from latest task in ${environment}..."
    
    # Get the latest task ARN
    local task_arn=$(aws ecs list-tasks \
        --region "$REGION" \
        --cluster "$cluster_name" \
        --service-name "$service_name" \
        --query 'taskArns[0]' \
        --output text)
    
    if [ "$task_arn" == "None" ] || [ -z "$task_arn" ]; then
        error "No running tasks found for service ${service_name}"
        return 1
    fi
    
    info "Task ARN: ${task_arn##*/}"
    
    # Get logs for this specific task
    local log_stream_prefix="ecs/${task_arn##*/}"
    local log_group="/ecs/${PROJECT_NAME}-${environment}"
    
    aws logs filter-log-events \
        --region "$REGION" \
        --log-group-name "$log_group" \
        --log-stream-name-prefix "$log_stream_prefix" \
        --max-items "$lines" \
        --query 'events[*].[timestamp,message]' \
        --output text | \
    tail -n "$lines" | \
    while IFS=$'\t' read -r timestamp message; do
        local readable_time=$(date -d "@$(($timestamp/1000))" +'%Y-%m-%d %I:%M:%S %p EST')
        echo -e "${GREEN}[$readable_time]${NC} $message"
    done
}

# Function to show usage
show_usage() {
    echo -e "${PURPLE}Calndr ECS Log Viewer${NC}"
    echo
    echo "Usage: $0 [command] [environment] [options]"
    echo
    echo "Commands:"
    echo "  stream <env>           - Stream live logs (like tail -f)"
    echo "  recent <env> [lines]   - Get recent logs (default: 100 lines)"
    echo "  errors <env> [hours]   - Search for errors (default: 24 hours)"
    echo "  search <env> <pattern> [hours] - Search logs for pattern"
    echo "  status <env>           - Get ECS service status"
    echo "  task <env> [lines]     - Get logs from latest task"
    echo "  list                   - List available environments"
    echo
    echo "Environments: staging, production"
    echo
    echo "Examples:"
    echo "  $0 stream staging                    # Stream live logs"
    echo "  $0 recent production 200             # Get last 200 log entries"
    echo "  $0 errors staging 12                 # Search errors in last 12 hours"
    echo "  $0 search production \"500\" 6        # Search for '500' in last 6 hours"
    echo "  $0 status staging                    # Get service status"
    echo "  $0 task production 100               # Get latest task logs"
}

# Main script logic
main() {
    check_aws_cli
    
    local command=$1
    local environment=$2
    
    case $command in
        "stream")
            if [ -z "$environment" ]; then
                error "Environment is required for stream command"
                show_usage
                exit 1
            fi
            stream_logs "$environment"
            ;;
        "recent")
            if [ -z "$environment" ]; then
                error "Environment is required for recent command"
                show_usage
                exit 1
            fi
            get_recent_logs "$environment" "$3" "${4:-1}"
            ;;
        "errors")
            if [ -z "$environment" ]; then
                error "Environment is required for errors command"
                show_usage
                exit 1
            fi
            search_errors "$environment" "${3:-24}"
            ;;
        "search")
            if [ -z "$environment" ] || [ -z "$3" ]; then
                error "Environment and search pattern are required"
                show_usage
                exit 1
            fi
            search_logs "$environment" "$3" "${4:-24}"
            ;;
        "status")
            if [ -z "$environment" ]; then
                error "Environment is required for status command"
                show_usage
                exit 1
            fi
            get_service_status "$environment"
            ;;
        "task")
            if [ -z "$environment" ]; then
                error "Environment is required for task command"
                show_usage
                exit 1
            fi
            get_task_logs "$environment" "${3:-50}"
            ;;
        "list")
            list_environments
            ;;
        *)
            show_usage
            ;;
    esac
}

# Run main function with all arguments
main "$@" 