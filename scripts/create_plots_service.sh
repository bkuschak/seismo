#!/bin/bash
#
# Periodically call the create plots script. Previously the script was called
# by cron, but that would cause problems if the script unexpectedly took too
# long to execute.

# First switch directory to the location of this script.
cd "$(dirname "$0")"

# Run at 10 minute intervals.
while true; do
    echo "===================================================================="
    ./create_plots.sh
    sleep 600
done
