# Calndr ECS Log Viewing Scripts

This directory contains powerful tools for easily viewing and analyzing logs from your ECS deployments. No more hunting through AWS console for the latest logs!

## 🚀 Quick Start

### Option 1: Use Quick Commands (Recommended)
```bash
# Stream live logs from staging
./scripts/quick-logs.sh live-staging

# Get latest 200 logs from production
./scripts/quick-logs.sh latest-prod

# Search for errors in staging (last 12 hours)
./scripts/quick-logs.sh errors-staging
```

### Option 2: Use Aliases (Super Fast!)
```bash
# Load aliases into your shell
source scripts/log-aliases.sh

# Now use short commands
lls    # Live staging logs
lrp    # Recent production logs
les    # Staging errors
```

### Option 3: Use Full Scripts (Advanced)
```bash
# Full control over log viewing
./scripts/view-logs.sh stream production
./scripts/view-logs.sh recent staging 500

# Advanced log analysis
./scripts/cloudwatch-insights.sh errors production 24
```

## 📁 Available Scripts

### 1. `quick-logs.sh` - Instant Log Access
Perfect for daily troubleshooting. Simple commands, no complex syntax.

**Available Commands:**
- `live-staging` (`ls`) - Stream live logs from staging
- `live-prod` (`lp`) - Stream live logs from production  
- `latest-staging` (`rs`) - Get latest 200 logs from staging
- `latest-prod` (`rp`) - Get latest 200 logs from production
- `errors-staging` (`es`) - Search errors in staging (last 12h)
- `errors-prod` (`ep`) - Search errors in production (last 12h)
- `status-staging` (`ss`) - Get staging service status
- `status-prod` (`sp`) - Get production service status

### 2. `view-logs.sh` - Comprehensive Log Viewer
Full-featured log viewing with customizable options.

**Available Commands:**
- `stream <env>` - Stream live logs (like tail -f)
- `recent <env> [lines] [hours]` - Get recent logs
- `errors <env> [hours]` - Search for errors
- `search <env> <pattern> [hours]` - Search logs for pattern
- `status <env>` - Get ECS service status
- `task <env> [lines]` - Get logs from latest task
- `list` - List available environments

**Examples:**
```bash
./scripts/view-logs.sh stream staging
./scripts/view-logs.sh recent production 500 2
./scripts/view-logs.sh search staging "database connection" 6
```

### 3. `cloudwatch-insights.sh` - Advanced Log Analysis
Use CloudWatch Insights for powerful log queries and analysis.

**Available Queries:**
- `errors <env> [hours]` - Error summary by time
- `slow <env> [hours]` - Slow requests (>1000ms)
- `endpoints <env> [hours]` - API endpoint usage statistics
- `database <env> [hours]` - Database-related errors
- `auth <env> [hours]` - Authentication issues
- `response <env> [hours]` - Response time statistics
- `custom <env> <query> [hours]` - Run custom CloudWatch Insights query

**Examples:**
```bash
./scripts/cloudwatch-insights.sh errors production 24
./scripts/cloudwatch-insights.sh slow staging 6
./scripts/cloudwatch-insights.sh endpoints production 12
```

### 4. `log-aliases.sh` - Shell Aliases
Source this file to add convenient aliases to your shell session.

```bash
source scripts/log-aliases.sh
```

**Available Aliases:**
- `lls` / `logs-live-staging` - Live staging logs
- `llp` / `logs-live-prod` - Live production logs
- `lrs` / `logs-recent-staging` - Recent staging logs
- `lrp` / `logs-recent-prod` - Recent production logs
- `les` / `logs-errors-staging` - Staging errors
- `lep` / `logs-errors-prod` - Production errors
- `lss` / `logs-status-staging` - Staging service status
- `lsp` / `logs-status-prod` - Production service status
- `logs` - Full log viewer script
- `insights` - CloudWatch Insights script

## 🎯 Common Use Cases

### Daily Troubleshooting
```bash
# Quick check of recent activity
./scripts/quick-logs.sh recent-prod

# Look for any errors
./scripts/quick-logs.sh errors-prod

# Check service health
./scripts/quick-logs.sh status-prod
```

### During Deployment
```bash
# Stream live logs to watch deployment
./scripts/quick-logs.sh live-staging

# Or with aliases (after sourcing)
source scripts/log-aliases.sh
lls  # Stream live staging logs
```

### Performance Investigation
```bash
# Find slow requests
./scripts/cloudwatch-insights.sh slow production 6

# Check response times
./scripts/cloudwatch-insights.sh response production 12

# API usage patterns
./scripts/cloudwatch-insights.sh endpoints production 24
```

### Error Investigation
```bash
# Recent errors with context
./scripts/view-logs.sh errors production 2

# Detailed error analysis
./scripts/cloudwatch-insights.sh errors production 24

# Search for specific error patterns
./scripts/view-logs.sh search production "500" 6
```

## 🔧 Setup Requirements

### Prerequisites
- AWS CLI installed and configured
- Appropriate IAM permissions for CloudWatch Logs
- Access to the ECS clusters (`calndr-staging-cluster`, `calndr-production-cluster`)

### Required IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:FilterLogEvents",
                "logs:StartQuery",
                "logs:StopQuery",
                "logs:GetQueryResults",
                "logs:GetLogEvents",
                "logs:TailLogs"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:*:log-group:/ecs/calndr-*",
                "arn:aws:logs:us-east-1:*:log-group:/ecs/calndr-*:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeServices",
                "ecs:DescribeTasks",
                "ecs:ListTasks"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🎨 Features

- **🌈 Color-coded output** - Errors in red, info in blue, timestamps in different colors
- **⏰ EST timestamps** - All times displayed in Eastern Time with AM/PM format
- **🔄 Real-time streaming** - Live log tailing like `tail -f`
- **🔍 Smart searching** - Pattern matching and filtering
- **📊 Advanced analytics** - CloudWatch Insights integration
- **⚡ Performance optimized** - Fast log retrieval and parsing
- **🛡️ Error handling** - Graceful failure with helpful error messages
- **📱 User-friendly** - Clear help text and examples

## 💡 Tips & Tricks

### 1. Add Aliases to Your Shell Profile
Add this to your `~/.zshrc` or `~/.bashrc` for permanent aliases:
```bash
# Calndr log aliases
source /path/to/your/project/scripts/log-aliases.sh
```

### 2. Common Troubleshooting Workflow
```bash
# 1. Check service status
lss  # or lsp for production

# 2. Look for recent errors
les  # or lep for production

# 3. Stream live logs if investigating
lls  # or llp for production

# 4. Deep dive with insights if needed
insights errors staging 24
```

### 3. Monitoring During Deployments
```bash
# Terminal 1: Watch deployment logs
lls

# Terminal 2: Monitor for errors
watch -n 30 './scripts/quick-logs.sh errors-staging'
```

### 4. Performance Monitoring
```bash
# Regular performance checks
insights response production 6
insights slow production 12
insights endpoints production 24
```

## 🚨 Troubleshooting

### AWS CLI Not Found
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Permission Denied
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### AWS Credentials Not Configured
```bash
# Configure AWS credentials
aws configure
```

### No Logs Found
- Check if the environment name is correct (`staging` or `production`)
- Verify ECS services are running
- Ensure log groups exist in CloudWatch

## 📚 Learn More

- [AWS CloudWatch Logs Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [CloudWatch Insights Query Syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [ECS Logging Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/logging.html)

---

**Happy Logging! 🎉**

These scripts will save you tons of time when troubleshooting your ECS deployments. No more clicking through the AWS console to find the latest logs! 