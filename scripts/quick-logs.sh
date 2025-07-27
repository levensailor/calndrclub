#!/bin/bash

# Quick Log Access Script for Calndr
# Shortcut commands for the most common log viewing tasks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIEW_LOGS_SCRIPT="$SCRIPT_DIR/view-logs.sh"

# Check if view-logs.sh exists
if [ ! -f "$VIEW_LOGS_SCRIPT" ]; then
    echo "Error: view-logs.sh not found at $VIEW_LOGS_SCRIPT"
    exit 1
fi

# Quick commands (no need to remember the full syntax)
case "$1" in
    "live-staging"|"ls")
        echo "🔴 Streaming live logs from STAGING..."
        "$VIEW_LOGS_SCRIPT" stream staging
        ;;
    "live-prod"|"lp")
        echo "🔴 Streaming live logs from PRODUCTION..."
        "$VIEW_LOGS_SCRIPT" stream production
        ;;
    "latest-staging"|"recent-staging"|"rs")
        echo "📋 Getting latest logs from STAGING..."
        "$VIEW_LOGS_SCRIPT" recent staging 200
        ;;
    "latest-prod"|"recent-prod"|"rp")
        echo "📋 Getting latest logs from PRODUCTION..."
        "$VIEW_LOGS_SCRIPT" recent production 200
        ;;
    "errors-staging"|"es")
        echo "❌ Searching for errors in STAGING..."
        "$VIEW_LOGS_SCRIPT" errors staging 12
        ;;
    "errors-prod"|"ep")
        echo "❌ Searching for errors in PRODUCTION..."
        "$VIEW_LOGS_SCRIPT" errors production 12
        ;;
    "status-staging"|"ss")
        echo "📊 Getting STAGING service status..."
        "$VIEW_LOGS_SCRIPT" status staging
        ;;
    "status-prod"|"sp")
        echo "📊 Getting PRODUCTION service status..."
        "$VIEW_LOGS_SCRIPT" status production
        ;;
    "help"|"h"|"")
        echo "🚀 Calndr Quick Log Access"
        echo
        echo "Quick Commands:"
        echo "  live-staging    (ls)  - Stream live logs from staging"
        echo "  live-prod       (lp)  - Stream live logs from production"
        echo "  latest-staging  (rs)  - Get latest 200 logs from staging"
        echo "  latest-prod     (rp)  - Get latest 200 logs from production"
        echo "  errors-staging  (es)  - Search errors in staging (last 12h)"
        echo "  errors-prod     (ep)  - Search errors in production (last 12h)"
        echo "  status-staging  (ss)  - Get staging service status"
        echo "  status-prod     (sp)  - Get production service status"
        echo
        echo "💡 For more advanced options, use: ./view-logs.sh"
        ;;
    *)
        echo "❓ Unknown command: $1"
        echo "Run './quick-logs.sh help' for available commands"
        exit 1
        ;;
esac 