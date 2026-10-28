"""NYSE (XNYS) trading calendar and the global walk-forward grid."""
from __future__ import annotations

from dataclasses import dataclass

import exchange_calendars as xc
import pandas as pd

from . import config


def sessions(start: str = config.DOWNLOAD_START, end: str = config.SNAPSHOT_END) -> pd.DatetimeIndex:
    cal = xc.get_calendar("XNYS")
    s = cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
    return pd.DatetimeIndex(s.tz_localize(None) if s.tz is not None else s)


@dataclass(frozen=True)
class Window:
    k: int
    fit_start: int     # index into sessions (inclusive)
    fit_end: int       # exclusive
    test_start: int    # inclusive
    test_end: int      # exclusive

    def dates(self, sess: pd.DatetimeIndex) -> dict:
        return {
            "k": self.k,
            "fit_start": sess[self.fit_start],
            "fit_end": sess[self.fit_end - 1],
            "test_start": sess[self.test_start],
            "test_end": sess[self.test_end - 1],
        }


def walk_forward_grid(sess: pd.DatetimeIndex, grid_start: str = config.GRID_START,
                      train_len: int = config.TRAIN_LEN, test_len: int = config.TEST_LEN) -> list[Window]:
    """Test windows start every `test_len` sessions beginning at `grid_start`; the training sample is
    the `train_len` sessions immediately before each start. The final window may be shorter."""
    i0 = int(sess.get_loc(pd.Timestamp(grid_start)))
    out = []
    k = 0
    n = len(sess)
    while True:
        ts = i0 + k * test_len
        if ts >= n:
            break
        te = min(ts + test_len, n)
        fs = ts - train_len
        if fs < 0:
            raise ValueError("not enough history for first training window")
        out.append(Window(k, fs, ts, ts, te))
        k += 1
    return out
