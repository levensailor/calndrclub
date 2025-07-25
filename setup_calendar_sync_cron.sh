#!/bin/bash
# Setup cron job for syncing school and daycare calendars

echo "Setting up cron job for calendar sync..."

# Get the absolute path to the sync script
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/sync_all_calendars.py"

# Create a cron job that runs daily at 6 AM
CRON_JOB="0 6 * * * cd $(dirname "$SCRIPT_PATH") && /usr/bin/python3 $SCRIPT_PATH >> logs/calendar_sync.log 2>&1"

# Check if the cron job already exists
if crontab -l 2>/dev/null | grep -q "sync_all_calendars.py"; then
    echo "Cron job already exists. Updating..."
    # Remove old cron job
    crontab -l | grep -v "sync_all_calendars.py" | crontab -
fi

# Add the new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job added successfully!"
echo "The sync will run daily at 6 AM."
echo ""
echo "To view current cron jobs: crontab -l"
echo "To run the sync manually: python3 $SCRIPT_PATH"
echo ""
echo "Logs will be saved to: $(dirname "$SCRIPT_PATH")/logs/calendar_sync.log"