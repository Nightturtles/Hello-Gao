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

# Stage and commit only what the simulator writes, so local edits to code in this clone (staged or not) are
# never pushed. sim/state may be absent (before the first warm start, or right after `ctl init --force` removed
# it): include it whenever it exists or git still tracks files under it, so a reset's deletions are pushed too.
sim_paths=(sim/config.json reports)
if [ -d sim/state ] || [ -n "$(git ls-files -- sim/state)" ]; then
  sim_paths+=(sim/state)
fi
git add --all -- "${sim_paths[@]}" || exit 1
if ! git diff --cached --quiet -- "${sim_paths[@]}"; then
  git commit -m "paper-sim: $(date -u +%Y-%m-%d) local launchd run" -- "${sim_paths[@]}" || exit 1
  # Rebase onto anything pushed meanwhile (e.g. by GitHub Actions); a stranded local commit would make the
  # next run's `git pull --ff-only` fail, so a failed rebase or push must not be silent.
  if ! { git pull --rebase --autostash origin "$BRANCH" && git push origin "$BRANCH"; }; then
    echo "could not push simulator state; resolve the clone at $REPO_DIR manually" >&2
    status=1
  fi
fi
exit $status
