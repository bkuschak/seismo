#!/bin/bash

echo "Killing earthworm..."
killall startstop
sleep 0.5
killall -w startstop
echo "Done"
