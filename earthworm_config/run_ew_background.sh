#!/bin/bash
# Start EW running in the background.  If this is run from a terminal, you can exit the 
# terminal session and EW will continue running.
#
# To stop EW, run ./stop_ew.sh
#

cd /opt/earthworm/earthworm_7.7/run_working/params
source ew_arm.bash
echo "Starting Earthworm"
exec nohup startstop > /dev/null 2>&1 &
