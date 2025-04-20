#!/bin/bash

# Get the absolute path of the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create crontab entry for daily reports at 00:05 each day
# This will run send_reports.py daily at 00:05 AM
CRON_JOB="5 0 * * * cd $SCRIPT_DIR && python send_reports.py >> $SCRIPT_DIR/reports.log 2>&1"

# Check if the cron job already exists
if crontab -l 2>/dev/null | grep -q "send_reports.py"; then
    echo "Cron job for reports already exists."
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job added for daily reports at 00:05 AM."
fi

echo "To manually send a report now, run:"
echo "python $SCRIPT_DIR/send_reports.py" 