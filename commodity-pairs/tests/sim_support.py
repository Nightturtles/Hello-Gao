"""Helpers shared by the simulator tests (no network: CacheProvider or synthetic data only)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import config
from backtest.trading_calendar import sessions
from sim import ctl, run_daily, store
from sim.data import CacheProvider, Provider
from sim.reports import BANNER

START = "2026-07-15"
END = "2026-10-26"
QUIET = lambda *a, **k: None  # noqa: E731


def real_picks() -> list[dict]:
    return store.load_picks()


def write_picks(path: Path, picks: list[dict]) -> Path:
    path.write_text(json.dumps({"picks": picks}))
    return path


def init(base, start: str = START, end: str = END, picks_path=None, *extra: str) -> int:
    args = ["init", "--start", start, "--end", end, "--base-dir", str(base), *extra]
    if picks_path:
        args += ["--picks", str(picks_path)]
    return ctl.main(args, out=QUIET)


def run(base, asof: str | None, provider="cache", now=None) -> int:
    return run_daily.run(str(base), provider, asof, now=now, out=QUIET)


def ctl_run(base, *args: str) -> tuple[int, list[str]]:
    lines: list[str] = []
    rc = ctl.main([*args, "--base-dir", str(base)], out=lambda *a: lines.append(" ".join(str(x) for x in a)))
    return rc, lines


def snapshot(base: Path) -> dict[str, bytes]:
    base = Path(base)
    return {str(p.relative_to(base)): p.read_bytes() for p in sorted(base.rglob("*")) if p.is_file()}


def copy_base(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def strip_run_stamps(snap: dict[str, bytes]) -> dict[str, str]:
    """Drop everything that legitimately differs between two runs of the same data: UTC run stamps."""
    out = {}
    for k, v in snap.items():
        text = v.decode("utf-8")
        if k.endswith("trades.csv"):
            text = "\n".join(line.split(",", 1)[1] if "," in line else line for line in text.splitlines())
        elif k.endswith(".md"):
            text = "\n".join(line for line in text.splitlines() if not line.startswith("_Generated"))
        elif k.endswith("config.json"):
            continue
        out[k] = text
    return out


def reports_under(base: Path) -> list[Path]:
    base = Path(base)
    out = sorted((base / "reports").rglob("*.md"))
    return out


def assert_banner(path: Path) -> None:
    first = path.read_text(encoding="utf-8").splitlines()[0]
    assert first == BANNER, f"{path} does not start with the banner"


class PatchedCache(CacheProvider):
    """The research cache with a per-ticker edit applied (drop a bar, wreck later prices, ...)."""

    def __init__(self, asof, patch=None):
        super().__init__(asof)
        self._patch = patch

    def _fetch(self, ticker):
        df = super()._fetch(ticker)
        return self._patch(ticker, df) if self._patch else df


def patched(patch):
    """Provider factory for ``run_daily.run(provider=...)``."""
    return lambda asof: PatchedCache(asof, patch)


class Synthetic(Provider):
    """Deterministic frames for fake tickers on the real NYSE calendar.  ``spec[ticker]`` is a function
    ``(sessions) -> (open, close)`` arrays; adjusted close equals close, no dividends or splits."""

    name = "synthetic"

    def __init__(self, asof, spec):
        super().__init__(asof)
        self.spec = spec

    def _fetch(self, ticker):
        sess = sessions(config.DOWNLOAD_START, self.asof)
        o, c = self.spec[ticker](sess)
        return pd.DataFrame({"open": o, "high": np.maximum(o, c), "low": np.minimum(o, c), "close": c,
                             "adjclose": c, "volume": 1e6, "dividends": 0.0, "splits": 0.0}, index=sess)
