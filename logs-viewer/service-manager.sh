#!/bin/bash

# CloudWatch Log Viewer Service Manager
# Easy management of the log viewer service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="com.levensailor.cloudwatch-log-viewer"
PLIST_FILE="$HOME/Library/LaunchAgents/com.levensailor.cloudwatch-log-viewer.plist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if service is installed
is_service_installed() {
    [[ -f "$PLIST_FILE" ]]
}

# Function to check if service is running
is_service_running() {
    launchctl list | grep -q "$SERVICE_NAME"
}

# Function to show service status
show_status() {
    print_status $BLUE "📊 CloudWatch Log Viewer Service Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if is_service_installed; then
        print_status $GREEN "✅ Service is installed"
        echo "   Config: $PLIST_FILE"
    else
        print_status $RED "❌ Service is not installed"
        echo "   Run: ./install-service.sh to install"
        return 1
    fi
    
    if is_service_running; then
        print_status $GREEN "✅ Service is running"
        echo "   Web Interface: http://localhost:8001"
        echo "   Health Check: http://localhost:8001/health"
    else
        print_status $YELLOW "⚠️  Service is not running"
    fi
    
    # Show recent logs
    if [[ -f "$SCRIPT_DIR/logs/service.log" ]]; then
        echo ""
        print_status $BLUE "📋 Recent Logs (last 5 lines):"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        tail -n 5 "$SCRIPT_DIR/logs/service.log" 2>/dev/null || echo "No logs available"
    fi
    
    # Show error logs if they exist
    if [[ -f "$SCRIPT_DIR/logs/service-error.log" ]]; then
        local error_count=$(wc -l < "$SCRIPT_DIR/logs/service-error.log" 2>/dev/null || echo "0")
        if [[ "$error_count" -gt 0 ]]; then
            echo ""
            print_status $YELLOW "⚠️  Error Logs (last 3 lines):"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            tail -n 3 "$SCRIPT_DIR/logs/service-error.log"
        fi
    fi
}

# Function to start the service
start_service() {
    print_status $BLUE "🚀 Starting CloudWatch Log Viewer Service..."
    
    if ! is_service_installed; then
        print_status $RED "❌ Service is not installed"
        echo "   Run: ./install-service.sh to install first"
        return 1
    fi
    
    if is_service_running; then
        print_status $YELLOW "⚠️  Service is already running"
        return 0
    fi
    
    launchctl start "$SERVICE_NAME"
    sleep 2
    
    if is_service_running; then
        print_status $GREEN "✅ Service started successfully!"
        echo "   Web Interface: http://localhost:8001"
    else
        print_status $RED "❌ Failed to start service"
        echo "   Check error logs: $SCRIPT_DIR/logs/service-error.log"
        return 1
    fi
}

# Function to stop the service
stop_service() {
    print_status $BLUE "🛑 Stopping CloudWatch Log Viewer Service..."
    
    if ! is_service_running; then
        print_status $YELLOW "⚠️  Service is not running"
        return 0
    fi
    
    launchctl stop "$SERVICE_NAME"
    sleep 2
    
    if ! is_service_running; then
        print_status $GREEN "✅ Service stopped successfully!"
    else
        print_status $RED "❌ Failed to stop service"
        return 1
    fi
}

# Function to restart the service
restart_service() {
    print_status $BLUE "🔄 Restarting CloudWatch Log Viewer Service..."
    
    if ! is_service_installed; then
        print_status $RED "❌ Service is not installed"
        echo "   Run: ./install-service.sh to install first"
        return 1
    fi
    
    # Stop if running
    if is_service_running; then
        launchctl stop "$SERVICE_NAME"
        sleep 2
    fi
    
    # Start the service
    launchctl start "$SERVICE_NAME"
    sleep 3
    
    if is_service_running; then
        print_status $GREEN "✅ Service restarted successfully!"
        echo "   Web Interface: http://localhost:8001"
    else
        print_status $RED "❌ Failed to restart service"
        echo "   Check error logs: $SCRIPT_DIR/logs/service-error.log"
        return 1
    fi
}

# Function to uninstall the service
uninstall_service() {
    print_status $BLUE "🗑️  Uninstalling CloudWatch Log Viewer Service..."
    
    if ! is_service_installed; then
        print_status $YELLOW "⚠️  Service is not installed"
        return 0
    fi
    
    # Stop if running
    if is_service_running; then
        launchctl stop "$SERVICE_NAME"
        sleep 2
    fi
    
    # Unload the service
    launchctl unload "$PLIST_FILE"
    
    # Remove the plist file
    rm -f "$PLIST_FILE"
    
    print_status $GREEN "✅ Service uninstalled successfully!"
}

# Function to show logs
show_logs() {
    local log_type=${1:-service}
    local lines=${2:-50}
    
    case $log_type in
        service|main)
            local log_file="$SCRIPT_DIR/logs/service.log"
            print_status $BLUE "📋 Service Logs (last $lines lines):"
            ;;
        error)
            local log_file="$SCRIPT_DIR/logs/service-error.log"
            print_status $BLUE "📋 Error Logs (last $lines lines):"
            ;;
        *)
            print_status $RED "❌ Invalid log type: $log_type"
            echo "   Valid types: service, error"
            return 1
            ;;
    esac
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ -f "$log_file" ]]; then
        tail -n "$lines" "$log_file"
    else
        print_status $YELLOW "⚠️  Log file not found: $log_file"
    fi
}

# Function to show help
show_help() {
    print_status $BLUE "🔧 CloudWatch Log Viewer Service Manager"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  status                    Show service status"
    echo "  start                     Start the service"
    echo "  stop                      Stop the service"
    echo "  restart                   Restart the service"
    echo "  uninstall                 Uninstall the service"
    echo "  logs [TYPE] [LINES]       Show service logs"
    echo "  help                      Show this help message"
    echo ""
    echo "Log Types:"
    echo "  service (default)         Show main service logs"
    echo "  error                     Show error logs"
    echo ""
    echo "Examples:"
    echo "  $0 status                 # Check service status"
    echo "  $0 start                  # Start the service"
    echo "  $0 logs service 100       # Show last 100 lines of service logs"
    echo "  $0 logs error             # Show error logs"
    echo ""
    echo "Service Information:"
    echo "  Web Interface: http://localhost:8001"
    echo "  Health Check: http://localhost:8001/health"
    echo "  Log Directory: $SCRIPT_DIR/logs/"
}

# Main script logic
case "${1:-help}" in
    status)
        show_status
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    uninstall)
        uninstall_service
        ;;
    logs)
        show_logs "$2" "$3"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_status $RED "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 