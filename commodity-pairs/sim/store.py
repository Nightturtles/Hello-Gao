"""Paths and persistence for the paper-trading simulator.

Every path derives from a *base directory* (default: the project root), so tests and dry runs can work in a
scratch directory and never touch the real ``sim/state`` or ``reports``::

    <base>/sim/config.json
    <base>/sim/state/{state.json, trades.csv, equity.csv, errors.log, warmup_<pick>.csv}
    <base>/reports/daily/YYYY-MM-DD.md, <base>/reports/summary.md, <base>/reports/final_sim_report.md

State and config are written atomically (temp file + rename).  The two CSV logs are append-only; ``repair`` drops
orphan rows left by a crash between "append rows" and "save state" so a re-run can never double-count a day.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import config as bconfig

PROJECT_ROOT: Path = bconfig.ROOT
PICKS_PATH: Path = PROJECT_ROOT / "sim" / "picks.json"

STATE_VERSION = 1

TRADE_COLS = ["run_utc", "session", "pick_id", "ticker", "side", "action", "shares", "price", "raw_open",
              "slippage", "commission", "reason", "signal_date"]
EQUITY_COLS = ["date", "pick_id", "equity", "cash", "shares_a", "shares_b", "close_a", "close_b", "z", "beta",
               "drawdown", "hwm", "state", "costs", "dividends", "queued_wa", "queued_wb", "queued_reason", "refit"]


class ConfigError(Exception):
    """No (valid) config.json: run ``python -m sim.ctl init`` first."""


@dataclass(frozen=True)
class Paths:
    base: Path

    @classmethod
    def of(cls, base=None) -> "Paths":
        return cls(Path(base) if base else PROJECT_ROOT)

    @property
    def config(self) -> Path:
        return self.base / "sim" / "config.json"

    @property
    def state_dir(self) -> Path:
        return self.base / "sim" / "state"

    @property
    def state(self) -> Path:
        return self.state_dir / "state.json"

    @property
    def trades(self) -> Path:
        return self.state_dir / "trades.csv"

    @property
    def equity(self) -> Path:
        return self.state_dir / "equity.csv"

    @property
    def errors(self) -> Path:
        return self.state_dir / "errors.log"

    def warmup(self, pick_id: str) -> Path:
        return self.state_dir / f"warmup_{pick_id}.csv"

    @property
    def reports(self) -> Path:
        return self.base / "reports"

    @property
    def daily_dir(self) -> Path:
        return self.reports / "daily"

    def daily(self, session) -> Path:
        return self.daily_dir / f"{pd.Timestamp(session).date()}.md"

    @property
    def summary(self) -> Path:
        return self.reports / "summary.md"

    @property
    def final(self) -> Path:
        return self.reports / "final_sim_report.md"


# --------------------------------------------------------------------------- atomic io
def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def dumps(obj) -> str:
    """Deterministic JSON (sorted keys, fixed indent) so identical state gives identical bytes."""
    return json.dumps(obj, indent=1, sort_keys=True, default=_json_default) + "\n"


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_text(path, dumps(obj))


# --------------------------------------------------------------------------- config
def load_config(paths: Paths) -> dict:
    if not paths.config.exists():
        raise ConfigError(f"{paths.config} not found: run `python -m sim.ctl init --start YYYY-MM-DD` first")
    return json.loads(paths.config.read_text(encoding="utf-8"))


def save_config(paths: Paths, cfg: dict) -> None:
    atomic_write_json(paths.config, cfg)


def load_picks(path: Path | None = None) -> list[dict]:
    p = Path(path) if path else PICKS_PATH
    return json.loads(p.read_text(encoding="utf-8"))["picks"]


# --------------------------------------------------------------------------- state
def empty_state() -> dict:
    return {"version": STATE_VERSION, "picks": {}}


def load_state(paths: Paths) -> dict:
    if not paths.state.exists():
        return empty_state()
    return json.loads(paths.state.read_text(encoding="utf-8"))


def save_state(paths: Paths, state: dict) -> None:
    atomic_write_json(paths.state, state)


# --------------------------------------------------------------------------- csv logs
def append_rows(path: Path, columns: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = (not path.exists()) or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n", extrasaction="raise")
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in columns})
        f.flush()


def read_equity(paths: Paths) -> pd.DataFrame:
    if not paths.equity.exists() or paths.equity.stat().st_size == 0:
        return pd.DataFrame(columns=EQUITY_COLS).astype({"date": "datetime64[ns]"})
    df = pd.read_csv(paths.equity, parse_dates=["date"],
                     dtype={"state": str, "queued_reason": str, "refit": str, "pick_id": str})
    for c in ("state", "queued_reason", "refit"):
        df[c] = df[c].fillna("")
    return df


def read_trades(paths: Paths) -> pd.DataFrame:
    if not paths.trades.exists() or paths.trades.stat().st_size == 0:
        return pd.DataFrame(columns=TRADE_COLS)
    df = pd.read_csv(paths.trades, dtype={"reason": str, "pick_id": str, "ticker": str, "side": str,
                                          "action": str, "session": str, "signal_date": str, "run_utc": str})
    df["reason"] = df["reason"].fillna("")
    return df


def read_errors(paths: Paths) -> list[str]:
    if not paths.errors.exists():
        return []
    return [ln for ln in paths.errors.read_text(encoding="utf-8").splitlines() if ln.strip()]


def log_errors(paths: Paths, lines: list[str]) -> None:
    if not lines:
        return
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    with open(paths.errors, "a", encoding="utf-8", newline="\n") as f:
        for ln in lines:
            f.write(ln.rstrip("\n") + "\n")


def repair(paths: Paths, state: dict) -> list[str]:
    """Drop rows written after a pick's saved ``last_processed`` (a crash between appending the CSV rows and saving
    the state).  Returns a description of what was dropped (empty if nothing)."""
    notes: list[str] = []
    lp = {pid: ps["last_processed"] for pid, ps in state.get("picks", {}).items()}
    if paths.equity.exists() and paths.equity.stat().st_size > 0:
        eq = read_equity(paths)
        keep = np.array([(r.pick_id in lp) and (r.date <= pd.Timestamp(lp[r.pick_id])) for r in eq.itertuples()],
                        dtype=bool)
        if not keep.all():
            notes.append(f"equity.csv: dropped {int((~keep).sum())} orphan row(s)")
            _rewrite_csv(paths.equity, EQUITY_COLS, eq[keep].assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d")))
    if paths.trades.exists() and paths.trades.stat().st_size > 0:
        tr = read_trades(paths)
        keep = np.array([(r.pick_id in lp) and (pd.Timestamp(r.session) <= pd.Timestamp(lp[r.pick_id]))
                         for r in tr.itertuples()], dtype=bool)
        if not keep.all():
            notes.append(f"trades.csv: dropped {int((~keep).sum())} orphan row(s)")
            _rewrite_csv(paths.trades, TRADE_COLS, tr[keep])
    return notes


def _rewrite_csv(path: Path, columns: list[str], df: pd.DataFrame) -> None:
    tmp = path.with_name(path.name + ".tmp")
    df[columns].to_csv(tmp, index=False, lineterminator="\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- init / force
def _n_files(p: Path) -> int:
    return sum(1 for f in p.rglob("*") if f.is_file()) if p.is_dir() else (1 if p.exists() else 0)


def sim_artifacts(paths: Paths) -> list[tuple[Path, int]]:
    """What a (re)start owns and would remove: config.json, the state directory, the sim's own reports.  Empty
    directories do not count; other files under reports/ (the research report, charts) are never touched."""
    out = []
    for p in (paths.config, paths.state_dir, paths.daily_dir, paths.summary, paths.final):
        n = _n_files(p)
        if n:
            out.append((p, n))
    return out


def remove_artifacts(paths: Paths) -> None:
    for p in (paths.state_dir, paths.daily_dir):
        if p.is_dir():
            shutil.rmtree(p)
    for p in (paths.summary, paths.final):
        if p.exists():
            p.unlink()
