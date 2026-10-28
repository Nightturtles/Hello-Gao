#!/usr/bin/env bash
# Remove the backup launchd job.
set -euo pipefail
LABEL="com.commoditypairs.sim"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Removed $LABEL."
