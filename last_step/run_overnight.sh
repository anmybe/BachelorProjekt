#!/bin/bash

# Prevent the system from sleeping while the script runs
# Instructions:
# 1. Connect your charger.
# 2. Run this script: ./run_overnight.sh
# 3. Turn your screen brightness down to zero (optional).
# 4. IMPORTANT: Leave the lid OPEN. (Closing the lid will still sleep the Mac unless you have an external monitor).

echo "Starting processing with 'caffeinate' to prevent sleep..."
echo "Please keep your charger connected and the lid OPEN."

# -i prevents the system from idle sleeping
caffeinate -i /usr/local/bin/python3 last_step/process_step4.py
