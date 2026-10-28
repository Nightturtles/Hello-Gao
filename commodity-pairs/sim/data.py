"""Price providers for the simulator.

``YahooProvider``  live data (yfinance, 4 attempts with exponential backoff).
``CacheProvider``  the frozen research cache in ``data/cache`` (used by tests and historical dry runs).

Both return a per-ticker frame indexed by session date with the cache columns
``open, high, low, close, adjclose, volume, dividends, splits`` and **never contain a bar after ``asof``**.
``close``/``open`` are the "raw" prices (split-adjusted by Yahoo, not dividend-adjusted); ``adjclose`` is the
dividend-adjusted close the rules trade on.
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass

import pandas as pd

from backtest import config
from backtest import data as bdata

VALUE_COLS = [c for c in bdata.CACHE_COLS if c != "date"]


class DataError(Exception):
    """A provider could not deliver usable data for a ticker (or a pick could not be advanced)."""


@dataclass(frozen=True)
class Issue:
    """One data problem found during a run (shown in the reports, appended to errors.log, makes the exit code 1)."""
    message: str
    pick_id: str | None = None
    session: str | None = None        # the session it blocked (None = not tied to one)

    def text(self) -> str:
        who = f"{self.pick_id}: " if self.pick_id else ""
        when = f"[{self.session}] " if self.session else ""
        return f"{who}{when}{self.message}"


def _clean(df: pd.DataFrame, asof: pd.Timestamp) -> pd.DataFrame:
    df = df.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for c in VALUE_COLS:
        if c not in df.columns:
            df[c] = 0.0 if c in ("dividends", "splits") else float("nan")
    df = df[VALUE_COLS].astype(float)
    return df.loc[:asof]


class Provider:
    """Base class.  Subclasses implement ``_fetch``; ``fetch`` memoises, cuts at ``asof`` and checks the frame."""

    name = "provider"

    def __init__(self, asof):
        self.asof = pd.Timestamp(asof).normalize()
        self._memo: dict[str, pd.DataFrame] = {}

    def _fetch(self, ticker: str) -> pd.DataFrame:  # pragma: no cover - interface
        raise NotImplementedError

    def fetch(self, ticker: str) -> pd.DataFrame:
        if ticker not in self._memo:
            df = _clean(self._fetch(ticker), self.asof)
            if df.empty:
                raise DataError(f"{ticker}: no bars on or before {self.asof.date()} ({self.name})")
            self._memo[ticker] = df
        return self._memo[ticker]


class CacheProvider(Provider):
    name = "cache"

    def _fetch(self, ticker: str) -> pd.DataFrame:
        df = bdata.load_ticker(ticker)
        if df is None:
            raise DataError(f"{ticker}: not in the research cache ({config.CACHE_DIR})")
        return df


def _yf_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=True)


class YahooProvider(Provider):
    """``Ticker(t).history(start=DOWNLOAD_START, end=asof+1 day, auto_adjust=False, actions=True)`` with retries.
    ``history_fn`` / ``sleep`` are injectable so the retry logic is testable without a network."""

    name = "yahoo"

    def __init__(self, asof, retries: int = 4, backoff: float = 2.0, history_fn=None, sleep=time.sleep):
        super().__init__(asof)
        self.retries, self.backoff = retries, backoff
        self._history = history_fn or _yf_history
        self._sleep = sleep

    def _fetch(self, ticker: str) -> pd.DataFrame:
        end = (self.asof + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        last = "no attempt made"
        for attempt in range(self.retries):
            try:
                h = self._history(ticker, config.DOWNLOAD_START, end)
                if h is not None and len(h) > 0:
                    df = bdata._normalise(h, end=str(self.asof.date()))
                    if len(df):
                        return df.set_index("date")
                last = "empty response"
            except Exception as e:  # noqa: BLE001 - any network/parse failure is retried
                last = f"{type(e).__name__}: {e}"
            if attempt < self.retries - 1:
                self._sleep(self.backoff * (2 ** attempt))
        raise DataError(f"{ticker}: yfinance failed after {self.retries} attempts ({last})")


PROVIDERS = {"yahoo": YahooProvider, "cache": CacheProvider}


def make_provider(spec, asof) -> Provider:
    """``spec`` is a provider name ("yahoo" | "cache") or a callable ``asof -> Provider`` (tests inject these)."""
    if callable(spec):
        return spec(pd.Timestamp(asof))
    if spec not in PROVIDERS:
        raise ValueError(f"unknown provider {spec!r}; choose from {sorted(PROVIDERS)}")
    return PROVIDERS[spec](asof)


def fetch_all(provider: Provider, tickers) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Fetch every ticker; a failure is recorded per ticker, never raised."""
    frames, errors = {}, {}
    for t in dict.fromkeys(tickers):
        try:
            frames[t] = provider.fetch(t)
        except DataError as e:
            errors[t] = str(e)
        except Exception as e:  # noqa: BLE001
            errors[t] = f"{t}: {type(e).__name__}: {e}"
    return frames, errors
