"""NYSE calendar helpers for the simulator (thin wrappers around exchange_calendars XNYS) and the close cutoff."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import exchange_calendars as xc
import pandas as pd

NY = ZoneInfo("America/New_York")
CLOSE_FINAL_AFTER = dt.time(16, 10)      # a session's close is treated as final from 16:10 New York time


def _cal():
    return xc.get_calendar("XNYS")


def _d(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return (t.tz_localize(None) if t.tz is not None else t).normalize()


def is_session(d) -> bool:
    return bool(_cal().is_session(_d(d)))


def last_session_on_or_before(d) -> pd.Timestamp:
    return _d(_cal().date_to_session(_d(d), direction="previous"))


def next_session_on_or_after(d) -> pd.Timestamp:
    return _d(_cal().date_to_session(_d(d), direction="next"))


def prev_session(d) -> pd.Timestamp:
    """The last session strictly before ``d`` (``d`` need not be a session)."""
    return last_session_on_or_before(_d(d) - pd.Timedelta(days=1))


def next_session(d) -> pd.Timestamp:
    """The first session strictly after ``d``."""
    return next_session_on_or_after(_d(d) + pd.Timedelta(days=1))


def nth_session_after(d, n: int) -> pd.Timestamp:
    """The session ``n`` sessions after session ``d`` (n >= 1)."""
    s = last_session_on_or_before(d)
    cal = _cal()
    for _ in range(n):
        s = _d(cal.next_session(s))
    return s


def sessions_between(first, last) -> pd.DatetimeIndex:
    """Sessions with first <= session <= last (empty if last < first)."""
    f, l = _d(first), _d(last)
    if l < f:
        return pd.DatetimeIndex([])
    s = _cal().sessions_in_range(f, l)
    return pd.DatetimeIndex(s.tz_localize(None) if s.tz is not None else s)


def default_asof(now: dt.datetime | None = None) -> pd.Timestamp:
    """The latest calendar date whose closing prices are final: today (New York) once it is past 16:10 New York time,
    else yesterday.  The caller only ever processes sessions <= this date (weekends and holidays have no session)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    ny = now.astimezone(NY)
    today = pd.Timestamp(ny.date())
    return today if ny.time() >= CLOSE_FINAL_AFTER else today - pd.Timedelta(days=1)
