#!/bin/bash
# Start EW running in the foreground. Used with /etc/inittab to start EW from init

cd /opt/earthworm/earthworm_7.7/run_working/params
source ew_arm.bash
echo "Starting Earthworm"
exec startstop > /dev/null 2>&1 
#exec startstop 
