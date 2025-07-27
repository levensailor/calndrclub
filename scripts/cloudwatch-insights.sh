#!/bin/bash

# CloudWatch Insights Queries for Calndr ECS Logs
# Advanced log analysis and troubleshooting

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

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %I:%M:%S %p EST')] $1${NC}"
}

# Function to run CloudWatch Insights query
run_insights_query() {
    local environment=$1
    local query=$2
    local hours=${3:-1}
    
    local log_group="/ecs/${PROJECT_NAME}-${environment}"
    local start_time=$(date -d "${hours} hours ago" --iso-8601)
    local end_time=$(date --iso-8601)
    
    info "Running CloudWatch Insights query on ${environment}..."
    info "Time range: ${start_time} to ${end_time}"
    echo
    
    # Start the query
    local query_id=$(aws logs start-query \
        --region "$REGION" \
        --log-group-name "$log_group" \
        --start-time "$(date -d "${hours} hours ago" +%s)" \
        --end-time "$(date +%s)" \
        --query-string "$query" \
        --query 'queryId' \
        --output text)
    
    if [ -z "$query_id" ]; then
        error "Failed to start query"
        return 1
    fi
    
    info "Query ID: $query_id"
    info "Waiting for results..."
    
    # Wait for query to complete and get results
    while true; do
        local status=$(aws logs get-query-results \
            --region "$REGION" \
            --query-id "$query_id" \
            --query 'status' \
            --output text)
        
        if [ "$status" = "Complete" ]; then
            break
        elif [ "$status" = "Failed" ]; then
            error "Query failed"
            return 1
        else
            echo -n "."
            sleep 2
        fi
    done
    
    echo
    log "Query completed! Results:"
    echo
    
    # Get and display results
    aws logs get-query-results \
        --region "$REGION" \
        --query-id "$query_id" \
        --query 'results' \
        --output table
}

# Predefined queries
query_errors_summary() {
    local environment=$1
    local hours=${2:-24}
    
    local query='fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
| sort @timestamp desc'
    
    log "Getting error summary for ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$query" "$hours"
}

query_slow_requests() {
    local environment=$1
    local hours=${2:-24}
    
    local query='fields @timestamp, @message
| filter @message like /took/
| parse @message "took * ms" as duration
| filter duration > 1000
| sort duration desc
| limit 20'
    
    log "Finding slow requests (>1000ms) in ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$query" "$hours"
}

query_api_endpoints() {
    local environment=$1
    local hours=${2:-6}
    
    local query='fields @timestamp, @message
| filter @message like /POST/ or @message like /GET/ or @message like /PUT/ or @message like /DELETE/
| parse @message "* * *" as method, endpoint, status
| stats count() by endpoint, method
| sort count desc
| limit 20'
    
    log "Getting API endpoint usage for ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$query" "$hours"
}

query_database_errors() {
    local environment=$1
    local hours=${2:-24}
    
    local query='fields @timestamp, @message
| filter @message like /database/ or @message like /postgres/ or @message like /connection/
| filter @message like /error/ or @message like /ERROR/ or @message like /failed/
| sort @timestamp desc
| limit 50'
    
    log "Finding database-related errors in ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$query" "$hours"
}

query_authentication_issues() {
    local environment=$1
    local hours=${2:-24}
    
    local query='fields @timestamp, @message
| filter @message like /auth/ or @message like /token/ or @message like /login/ or @message like /unauthorized/
| filter @message like /error/ or @message like /ERROR/ or @message like /failed/ or @message like /401/ or @message like /403/
| sort @timestamp desc
| limit 50'
    
    log "Finding authentication issues in ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$query" "$hours"
}

query_response_times() {
    local environment=$1
    local hours=${2:-6}
    
    local query='fields @timestamp, @message
| filter @message like /took/
| parse @message "took * ms" as duration
| stats avg(duration), max(duration), min(duration), count() by bin(5m)
| sort @timestamp desc'
    
    log "Getting response time statistics for ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$query" "$hours"
}

query_custom() {
    local environment=$1
    local custom_query=$2
    local hours=${3:-24}
    
    log "Running custom query on ${environment} (last ${hours} hours)..."
    run_insights_query "$environment" "$custom_query" "$hours"
}

show_usage() {
    echo -e "${PURPLE}Calndr CloudWatch Insights Queries${NC}"
    echo
    echo "Usage: $0 [query] [environment] [hours]"
    echo
    echo "Predefined Queries:"
    echo "  errors <env> [hours]        - Error summary by time"
    echo "  slow <env> [hours]          - Slow requests (>1000ms)"
    echo "  endpoints <env> [hours]     - API endpoint usage"
    echo "  database <env> [hours]      - Database errors"
    echo "  auth <env> [hours]          - Authentication issues"
    echo "  response <env> [hours]      - Response time statistics"
    echo "  custom <env> <query> [hours] - Run custom CloudWatch Insights query"
    echo
    echo "Environments: staging, production"
    echo "Default hours: varies by query type"
    echo
    echo "Examples:"
    echo "  $0 errors staging 12          # Error summary for last 12 hours"
    echo "  $0 slow production 6          # Slow requests in last 6 hours"
    echo "  $0 endpoints staging          # API usage in last 6 hours (default)"
    echo "  $0 custom staging 'fields @message | limit 10' 1"
    echo
    echo "💡 CloudWatch Insights provides powerful log analysis capabilities"
    echo "   Learn more: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html"
}

# Main script logic
main() {
    local query_type=$1
    local environment=$2
    
    case $query_type in
        "errors")
            if [ -z "$environment" ]; then
                error "Environment is required"
                show_usage
                exit 1
            fi
            query_errors_summary "$environment" "${3:-24}"
            ;;
        "slow")
            if [ -z "$environment" ]; then
                error "Environment is required"
                show_usage
                exit 1
            fi
            query_slow_requests "$environment" "${3:-24}"
            ;;
        "endpoints")
            if [ -z "$environment" ]; then
                error "Environment is required"
                show_usage
                exit 1
            fi
            query_api_endpoints "$environment" "${3:-6}"
            ;;
        "database"|"db")
            if [ -z "$environment" ]; then
                error "Environment is required"
                show_usage
                exit 1
            fi
            query_database_errors "$environment" "${3:-24}"
            ;;
        "auth"|"authentication")
            if [ -z "$environment" ]; then
                error "Environment is required"
                show_usage
                exit 1
            fi
            query_authentication_issues "$environment" "${3:-24}"
            ;;
        "response"|"perf"|"performance")
            if [ -z "$environment" ]; then
                error "Environment is required"
                show_usage
                exit 1
            fi
            query_response_times "$environment" "${3:-6}"
            ;;
        "custom")
            if [ -z "$environment" ] || [ -z "$3" ]; then
                error "Environment and custom query are required"
                show_usage
                exit 1
            fi
            query_custom "$environment" "$3" "${4:-24}"
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

# Run main function
main "$@" 