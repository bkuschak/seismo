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

    # If for some reason the script stalls, kill it after 2 hours so it
    # doesn't hang our loop.
    /usr/bin/timeout -k30s 2h ./create_plots.sh
    RET=$?
    if [ "${RET}" == "124" ]; then
        echo "Timeout! Killed create_plots.sh due to excessive runtime."
    fi

    echo "Sleeping until next time..."
    sleep 600
done
