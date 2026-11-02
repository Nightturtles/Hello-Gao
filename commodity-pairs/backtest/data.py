"""Data download, cache, load and QA (spec section 1).

Research code reads only the gzipped CSV cache in ``data/cache``; the network is touched only by
``python -m backtest.data --download``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import warnings

import numpy as np
import pandas as pd

from . import config
from .trading_calendar import sessions as nyse_sessions

CACHE_COLS = ["date", "open", "high", "low", "close", "adjclose", "volume", "dividends", "splits"]


# --------------------------------------------------------------------------- tickers
def candidate_pairs() -> pd.DataFrame:
    return pd.read_csv(config.CANDIDATES_PATH)


def all_tickers(include_benchmarks: bool = True) -> list[str]:
    c = candidate_pairs()
    t = set(c.leg_a) | set(c.leg_b)
    if include_benchmarks:
        t |= set(config.BENCHMARKS)
    return sorted(t)


# --------------------------------------------------------------------------- cache io
def cache_path(ticker: str):
    return config.CACHE_DIR / f"{ticker}.csv.gz"


def _write_cache(ticker: str, df: pd.DataFrame) -> None:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # mtime=0 makes the gzip bytes (and hence the sha256) deterministic
    df.to_csv(cache_path(ticker), index=False, compression={"method": "gzip", "mtime": 0})


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ticker(ticker: str) -> pd.DataFrame | None:
    """Load one ticker from the cache (None if absent or empty)."""
    p = cache_path(ticker)
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    if df.empty:
        return None
    return df.set_index("date").sort_index()


def with_adjopen(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["adjopen"] = out["open"] * out["adjclose"] / out["close"]
    return out


# --------------------------------------------------------------------------- download
def _download_one(ticker: str, retries: int = 4) -> tuple[pd.DataFrame | None, str]:
    import yfinance as yf

    last_err = ""
    for attempt in range(retries):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                h = yf.Ticker(ticker).history(start=config.DOWNLOAD_START, end=config.DOWNLOAD_END,
                                              auto_adjust=False, actions=True)
            if h is not None and len(h) > 0:
                return h, ""
            last_err = "empty response"
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(2 ** attempt)
    return None, last_err


def _normalise(h: pd.DataFrame, end: str | None = None) -> pd.DataFrame:
    """yfinance history -> cache columns, dates tz-naive, capped at `end` (default: the research snapshot end).
    The live simulator passes its own `end`."""
    h = h.copy()
    idx = pd.DatetimeIndex(h.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    h.index = idx.normalize()
    out = pd.DataFrame({
        "date": h.index,
        "open": h["Open"].to_numpy(),
        "high": h["High"].to_numpy(),
        "low": h["Low"].to_numpy(),
        "close": h["Close"].to_numpy(),
        "adjclose": h["Adj Close"].to_numpy(),
        "volume": h["Volume"].to_numpy(),
        "dividends": h["Dividends"].to_numpy() if "Dividends" in h else 0.0,
        "splits": h["Stock Splits"].to_numpy() if "Stock Splits" in h else 0.0,
    })
    out = out[out["date"] <= pd.Timestamp(end or config.SNAPSHOT_END)]
    out = out.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    return out[CACHE_COLS]


def download(tickers: list[str] | None = None, force: bool = False, with_info: bool = True) -> dict:
    tickers = tickers or all_tickers()
    manifest = json.loads(config.MANIFEST_PATH.read_text()) if config.MANIFEST_PATH.exists() else {}
    for i, t in enumerate(tickers):
        if not force and t in manifest and manifest[t].get("rows", 0) > 0 and cache_path(t).exists():
            print(f"[{i + 1}/{len(tickers)}] {t}: cached, skip")
            continue
        h, err = _download_one(t)
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        if h is None:
            manifest[t] = {"source": "yfinance", "download_utc": now, "status": "no_data", "rows": 0,
                           "first": None, "last": None, "sha256": None, "error": err}
            print(f"[{i + 1}/{len(tickers)}] {t}: NO DATA ({err})")
        else:
            df = _normalise(h)
            _write_cache(t, df)
            manifest[t] = {"source": "yfinance", "download_utc": now, "status": "ok", "rows": int(len(df)),
                           "first": str(df.date.iloc[0].date()), "last": str(df.date.iloc[-1].date()),
                           "sha256": sha256_file(cache_path(t)), "error": ""}
            print(f"[{i + 1}/{len(tickers)}] {t}: {len(df)} rows {manifest[t]['first']} -> {manifest[t]['last']}")
        config.MANIFEST_PATH.write_text(json.dumps(dict(sorted(manifest.items())), indent=1))
    if with_info:
        download_info(tickers, force=force)
    return manifest


def download_info(tickers: list[str], force: bool = False) -> dict:
    import yfinance as yf

    info = json.loads(config.INFO_PATH.read_text()) if config.INFO_PATH.exists() else {}
    for t in tickers:
        if not force and t in info and info[t].get("quoteType"):
            continue
        rec = {"quoteType": None, "longName": None, "exchange": None, "error": ""}
        for attempt in range(4):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    d = yf.Ticker(t).info
                rec.update({"quoteType": d.get("quoteType"), "longName": d.get("longName") or d.get("shortName"),
                            "exchange": d.get("exchange"), "error": ""})
                if rec["quoteType"]:
                    break
                rec["error"] = "no quoteType in info"
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
        info[t] = rec
        print(f"info {t}: {rec['quoteType']} {rec['error']}")
        config.INFO_PATH.write_text(json.dumps(dict(sorted(info.items())), indent=1))
    return info


def verify_manifest() -> list[str]:
    """Return a list of problems comparing the cache with MANIFEST.json (empty = consistent)."""
    problems = []
    if not config.MANIFEST_PATH.exists():
        return ["MANIFEST.json missing"]
    m = json.loads(config.MANIFEST_PATH.read_text())
    for t, rec in m.items():
        if rec.get("rows", 0) > 0:
            p = cache_path(t)
            if not p.exists():
                problems.append(f"{t}: cache file missing")
            elif sha256_file(p) != rec["sha256"]:
                problems.append(f"{t}: sha256 mismatch")
    return problems


# --------------------------------------------------------------------------- panel
def load_all(tickers: list[str]) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Load cached tickers. Returns (frames, missing{ticker: reason})."""
    manifest = json.loads(config.MANIFEST_PATH.read_text()) if config.MANIFEST_PATH.exists() else {}
    frames, missing = {}, {}
    for t in tickers:
        df = load_ticker(t)
        if df is None:
            rec = manifest.get(t, {})
            missing[t] = f"no data in cache ({rec.get('error') or rec.get('status') or 'not downloaded'})"
        else:
            frames[t] = with_adjopen(df)
    return frames, missing


def build_panel(frames: dict[str, pd.DataFrame], sess: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    """field -> DataFrame(sessions x tickers); NaN where a ticker has no bar on that NYSE session."""
    fields = ["open", "close", "adjclose", "adjopen", "volume"]
    out = {}
    for f in fields:
        out[f] = pd.DataFrame({t: df[f].reindex(sess) for t, df in frames.items()}, index=sess)
    return out


# --------------------------------------------------------------------------- QA
def _used_start(df: pd.DataFrame, sess: pd.DatetimeIndex, windows) -> pd.Timestamp:
    """First training-sample date the walk-forward can ever use for this ticker on its own."""
    have = pd.Series(df[["open", "close", "adjclose"]].notna().all(axis=1)).reindex(sess).fillna(False).to_numpy()
    for w in windows:
        if have[w.fit_start:w.test_end].all():
            return sess[w.fit_start]
    return sess[-1] + pd.Timedelta(days=1)   # never usable


def qa_ticker(t: str, df: pd.DataFrame, sess: pd.DatetimeIndex, windows=None) -> list[dict]:
    """Return QA rows. severity: 'error' (unresolved -> the leg is excluded), 'warning', 'info'.

    An issue dated before the first training sample the walk-forward can use (``used_start``) is
    reported as a warning, not an error, because that data never enters any fit or fill."""
    rows = []
    used_start = _used_start(df, sess, windows) if windows else df.index[0]

    def add(check, dates, count=None, detail="", warn_only=False):
        dates = list(dates)
        n_ = len(dates) if count is None else count
        if n_ == 0:
            sev = "info"
        elif warn_only:
            sev = "warning"
        elif max(dates) >= used_start:
            sev = "error"
        else:
            sev = "warning"
            detail = (detail + " [before first usable training sample " + str(used_start.date()) + "; not used]").strip()
        rows.append({"ticker": t, "check": check, "severity": sev, "count": int(n_), "detail": detail})

    def info(check, count, detail=""):
        rows.append({"ticker": t, "check": check, "severity": "info", "count": int(count), "detail": detail})

    n = len(df)
    px_cols = ["open", "high", "low", "close", "adjclose"]
    # zero / negative prices
    bad = (df[px_cols] <= 0).any(axis=1)
    add("nonpositive_price", df.index[bad], detail=";".join(str(d.date()) for d in df.index[bad][:10]))
    # NaNs
    nan_rows = df[px_cols].isna().any(axis=1)
    add("nan_price", df.index[nan_rows], detail=";".join(str(d.date()) for d in df.index[nan_rows][:10]))
    # OHLC consistency
    tol = 1e-6
    inc = (df["high"] < df["low"] - tol) | (df["close"] > df["high"] * 1.01 + tol) | (df["close"] < df["low"] * 0.99 - tol)
    add("ohlc_inconsistent", df.index[inc], detail=";".join(str(d.date()) for d in df.index[inc][:10]))
    # runs of >=5 identical closes; "stale" (error) when at least half of the run's days have zero volume
    c = df["close"].to_numpy()
    runs = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and c[j + 1] == c[i]:
            j += 1
        if j - i + 1 >= 5:
            zero_days = int((df["volume"].iloc[i:j + 1] == 0).sum())
            runs.append((df.index[i], df.index[j], j - i + 1, zero_days))
        i = j + 1
    stale = [r for r in runs if r[3] * 2 >= r[2]]
    detail = ";".join(f"{d0.date()}x{k}(zero-vol {z})" for d0, _, k, z in runs[:10])
    if stale:
        add("identical_close_run_ge5", [r[1] for r in stale], count=len(runs), detail=detail)
    else:
        add("identical_close_run_ge5", [r[1] for r in runs], count=len(runs), detail=detail, warn_only=True)
    # large adjclose moves, cross-checked against splits and the raw (split-adjusted, dividend-unadjusted) close
    ret = df["adjclose"].pct_change()
    rawret = df["close"].pct_change()
    big = ret.abs() > 0.25
    split_dates = set(df.index[df["splits"].fillna(0) != 0])
    big_info, err_dates = [], []
    for d in df.index[big.fillna(False)]:
        k = df.index.get_loc(d)
        near_dates = [df.index[min(max(k + o, 0), n - 1)] for o in (-1, 0, 1)]
        near_splits = [float(df.loc[x, "splits"]) for x in near_dates if x in split_dates]
        mismatch = bool(abs(ret.loc[d] - rawret.loc[d]) > 0.10)
        factor = 1.0 + float(ret.loc[d])
        # an unadjusted split would show up as a price factor ~ 1/ratio (e.g. 0.5 for a 2:1 split)
        artifact = any(r != 0 and abs(factor * r - 1.0) < 0.25 for r in near_splits)
        if artifact:
            status = "SPLIT_ADJUSTMENT_SUSPECT"
            err_dates.append(d)
        elif factor >= 10.0 or factor <= 0.1:
            # a 10x one-day move with no split is a different security spliced under one ticker (e.g. CHRD: the
            # cancelled pre-bankruptcy Oasis equity at $0.12 followed by the reorganised shares at $34)
            status = "SECURITY_SPLICE_SUSPECT"
            err_dates.append(d)
        elif mismatch:
            status = "RAW_ADJ_MISMATCH"
            err_dates.append(d)
        elif near_splits:
            status = "split_nearby_move_not_split_sized"
        else:
            status = "genuine_large_move_no_split"
        big_info.append(f"{d.date()}:{ret.loc[d]:+.1%}:{status}")
    if err_dates:
        add("abs_adjret_gt_25pct", err_dates, count=len(big_info), detail=";".join(big_info[:12]))
    else:
        add("abs_adjret_gt_25pct", list(df.index[big.fillna(False)]), count=len(big_info),
            detail=";".join(big_info[:12]), warn_only=True)
    if split_dates:
        info("splits_in_history", len(split_dates), ";".join(f"{d.date()}:{df.loc[d, 'splits']}" for d in sorted(split_dates)))
    # calendar gaps inside the ticker's own span
    span = sess[(sess >= df.index[0]) & (sess <= df.index[-1])]
    missing = span.difference(df.index)
    extra = df.index.difference(sess)
    frac = len(missing) / max(len(span), 1)
    gap_detail = ";".join(str(d.date()) for d in missing[:15])
    if frac > 0.02:
        add("missing_nyse_sessions", list(missing), detail=gap_detail)
    else:
        add("missing_nyse_sessions", list(missing), detail=gap_detail, warn_only=True)
    add("non_session_dates", list(extra), detail=";".join(str(d.date()) for d in extra[:15]), warn_only=True)
    add("last_bar_date", [df.index[-1]] if df.index[-1] < sess[-1] else [], detail=str(df.index[-1].date()), warn_only=True)
    info("zero_volume_days", int((df["volume"] == 0).sum()))
    info("rows", n, f"{df.index[0].date()} -> {df.index[-1].date()}; first usable training sample {used_start.date()}")
    return rows


def run_qa(frames: dict[str, pd.DataFrame], missing: dict[str, str], sess: pd.DatetimeIndex, windows=None) -> pd.DataFrame:
    rows = []
    for t in sorted(frames):
        rows.extend(qa_ticker(t, frames[t], sess, windows))
    for t, why in sorted(missing.items()):
        rows.append({"ticker": t, "check": "ticker_available", "severity": "error", "count": 0, "detail": why})
    return pd.DataFrame(rows, columns=["ticker", "check", "severity", "count", "detail"])


def unresolved_errors(qa: pd.DataFrame) -> dict[str, str]:
    e = qa[qa.severity == "error"]
    return {t: "; ".join(f"{r.check}({r.count})" for r in g.itertuples()) for t, g in e.groupby("ticker")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="download missing tickers into the cache")
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument("--tickers", nargs="*", help="subset of tickers")
    ap.add_argument("--info-only", action="store_true")
    ap.add_argument("--verify", action="store_true", help="verify cache sha256 against MANIFEST.json")
    args = ap.parse_args()
    if args.verify:
        probs = verify_manifest()
        print("OK" if not probs else "\n".join(probs))
        sys.exit(1 if probs else 0)
    if args.download:
        if args.info_only:
            download_info(args.tickers or all_tickers(), force=args.force)
        else:
            download(args.tickers, force=args.force)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
