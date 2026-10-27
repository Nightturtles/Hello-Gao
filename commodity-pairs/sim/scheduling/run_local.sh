#!/usr/bin/env bash
# Backup scheduler: run one paper-trading day from a local clone (used by launchd).
# Pull first so this run sees state from any GitHub Actions run. The simulator is
# idempotent, so if Actions already processed today this run changes nothing.
# Enable only one scheduler at a time anyway (see sim/scheduling/README.md).
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
BRANCH="${PAPER_SIM_BRANCH:-master}"
PYTHON="$PROJECT_DIR/.venv/bin/python"

cd "$REPO_DIR" || exit 1
echo "=== paper-sim local run $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

git checkout "$BRANCH" && git pull --ff-only origin "$BRANCH" || {
  echo "git pull failed; not running, so local state cannot diverge from the remote" >&2
  exit 1
}

if [ ! -x "$PYTHON" ]; then
  python3 -m venv "$PROJECT_DIR/.venv" && "$PYTHON" -m pip install -q -r "$PROJECT_DIR/requirements.txt" || exit 1
fi

cd "$PROJECT_DIR"
"$PYTHON" -m sim.run_daily
status=$?

git add sim/state sim/config.json reports
if ! git diff --cached --quiet; then
  git commit -m "paper-sim: $(date -u +%Y-%m-%d) local launchd run" && git push origin "$BRANCH"
fi
exit $status
