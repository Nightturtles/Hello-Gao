"""Price providers for the simulator.

``YahooProvider``  live data (yfinance, 4 attempts with exponential backoff).
``CacheProvider``  the frozen research cache in ``data/cache`` (used by tests and historical dry runs).

Both return a per-ticker frame indexed by session date with the cache columns
``open, high, low, close, adjclose, volume, dividends, splits`` and **never contain a bar after ``asof``**.
``adjclose`` is the split- and dividend-adjusted close the rules trade on.  ``open``/``close`` are the raw prices
the engine fills and marks at.  The engine applies a split itself on its date, so ``YahooProvider`` returns them **as
traded** on each date (see ``as_traded``): Yahoo restates every earlier bar once a split takes effect, so a session
processed after its next-day split would otherwise be priced on the post-split basis with pre-split share counts.
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass

import pandas as pd

from backtest import config
from backtest import data as bdata

VALUE_COLS = [c for c in bdata.CACHE_COLS if c != "date"]
_NO_CAP = "2200-01-01"      # bdata._normalise caps at the research snapshot end by default; live data keeps every bar


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


def _yf_history(ticker: str, start: str, end: str | None) -> pd.DataFrame:
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=True)


def as_traded(df: pd.DataFrame) -> pd.DataFrame:
    """Undo Yahoo's backward split adjustment of the raw columns: every row is multiplied by the product of the split
    ratios dated strictly AFTER it (prices and per-share dividends; volume divided), so each bar is on the share basis
    that applied on its own date and the engine's own split step (shares x ratio on the split date) is the only one.
    ``adjclose`` is left as Yahoo gives it: the rules trade on it, exactly as in the backtest.  A split dated after
    ``asof`` is the only thing read from bars after ``asof``; it is announced in advance, so this is not look-ahead."""
    r = df["splits"].astype(float)
    r = r.where(r > 0.0, 1.0).fillna(1.0)
    after = r[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)       # product of the ratios strictly after each row
    out = df.copy()
    for c in ("open", "high", "low", "close", "dividends"):
        out[c] = out[c].astype(float) * after
    out["volume"] = out["volume"].astype(float) / after
    return out


class YahooProvider(Provider):
    """``Ticker(t).history(start=DOWNLOAD_START, end=None, auto_adjust=False, actions=True)`` with retries, converted
    to as-traded raw prices (``as_traded``) and then cut at ``asof``.  The request runs to the latest bar, not to
    ``asof``, so that a split after ``asof`` (which Yahoo has already applied to every earlier bar) is seen.
    ``history_fn`` / ``sleep`` are injectable so the retry logic is testable without a network."""

    name = "yahoo"

    def __init__(self, asof, retries: int = 4, backoff: float = 2.0, history_fn=None, sleep=time.sleep):
        super().__init__(asof)
        self.retries, self.backoff = retries, backoff
        self._history = history_fn or _yf_history
        self._sleep = sleep

    def _fetch(self, ticker: str) -> pd.DataFrame:
        last = "no attempt made"
        for attempt in range(self.retries):
            try:
                h = self._history(ticker, config.DOWNLOAD_START, None)
                if h is not None and len(h) > 0:
                    df = bdata._normalise(h, end=_NO_CAP)
                    if len(df):
                        return as_traded(df.set_index("date"))      # Provider.fetch then cuts at asof
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
