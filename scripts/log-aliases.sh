# Calndr Log Viewing Aliases
# Source this file to add convenient aliases to your shell
# Usage: source scripts/log-aliases.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Quick access aliases
alias logs-live-staging='$SCRIPT_DIR/quick-logs.sh live-staging'
alias logs-live-prod='$SCRIPT_DIR/quick-logs.sh live-prod'
alias logs-recent-staging='$SCRIPT_DIR/quick-logs.sh recent-staging'
alias logs-recent-prod='$SCRIPT_DIR/quick-logs.sh recent-prod'
alias logs-errors-staging='$SCRIPT_DIR/quick-logs.sh errors-staging'
alias logs-errors-prod='$SCRIPT_DIR/quick-logs.sh errors-prod'
alias logs-status-staging='$SCRIPT_DIR/quick-logs.sh status-staging'
alias logs-status-prod='$SCRIPT_DIR/quick-logs.sh status-prod'

# Short aliases (even quicker!)
alias lls='$SCRIPT_DIR/quick-logs.sh live-staging'
alias llp='$SCRIPT_DIR/quick-logs.sh live-prod'
alias lrs='$SCRIPT_DIR/quick-logs.sh recent-staging'
alias lrp='$SCRIPT_DIR/quick-logs.sh recent-prod'
alias les='$SCRIPT_DIR/quick-logs.sh errors-staging'
alias lep='$SCRIPT_DIR/quick-logs.sh errors-prod'
alias lss='$SCRIPT_DIR/quick-logs.sh status-staging'
alias lsp='$SCRIPT_DIR/quick-logs.sh status-prod'

# Full script aliases
alias logs='$SCRIPT_DIR/view-logs.sh'
alias insights='$SCRIPT_DIR/cloudwatch-insights.sh'

echo "✅ Calndr log viewing aliases loaded!"
echo
echo "Quick aliases available:"
echo "  lls / logs-live-staging     - Stream live staging logs"
echo "  llp / logs-live-prod        - Stream live production logs"
echo "  lrs / logs-recent-staging   - Get recent staging logs"
echo "  lrp / logs-recent-prod      - Get recent production logs"
echo "  les / logs-errors-staging   - Search staging errors"
echo "  lep / logs-errors-prod      - Search production errors"
echo "  lss / logs-status-staging   - Get staging service status"
echo "  lsp / logs-status-prod      - Get production service status"
echo
echo "Full scripts:"
echo "  logs [command] [env]        - Full log viewer"
echo "  insights [query] [env]      - CloudWatch Insights queries"
echo
echo "💡 Run any alias without parameters for help" 