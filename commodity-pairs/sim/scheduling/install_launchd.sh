#!/usr/bin/env bash
# Install the backup launchd job on macOS. Run once from your local clone:
#   bash commodity-pairs/sim/scheduling/install_launchd.sh
# Before installing, disable the GitHub Actions schedule so only one scheduler runs:
# GitHub -> Actions -> paper-sim -> "..." -> Disable workflow.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.commoditypairs.sim"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/commodity-pairs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
chmod +x "$HERE/run_local.sh"
sed -e "s#__RUN_SCRIPT__#$HERE/run_local.sh#" -e "s#__LOG_DIR__#$LOG_DIR#" \
  "$HERE/$LABEL.plist" > "$DEST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "Installed $DEST. It runs Mon-Fri at 13:35 local time; logs are in $LOG_DIR."
echo "Run it once now:   launchctl kickstart -k gui/$(id -u)/$LABEL"
echo "Remove it:         bash $HERE/uninstall_launchd.sh"
