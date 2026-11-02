"""Live-vs-backtest statistics used by the final report."""
import numpy as np
import pandas as pd
import pytest

from backtest import config
from sim import compare

from .sim_support import real_picks


def test_rolling_window_returns_and_percentile():
    r = np.array([0.10, -0.10, 0.05, 0.05])
    w = compare.rolling_window_returns(r, 2)
    assert w == pytest.approx([1.1 * 0.9 - 1, 0.9 * 1.05 - 1, 1.05 * 1.05 - 1])
    assert compare.rolling_window_returns(r, 5).size == 0 and compare.rolling_window_returns(r, 0).size == 0
    assert compare.percentile_of(0.0, w) == pytest.approx(100 * 2 / 3)          # two of three windows are <= 0
    assert np.isnan(compare.percentile_of(0.0, np.array([])))


def test_monthly_stats_compound_by_calendar_month():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01", "2024-02-02", "2024-03-01"])
    r = pd.Series([0.01, 0.01, 0.02, -0.01, 0.03], index=idx)
    mean, sd, n = compare.monthly_stats(r)
    months = np.array([1.01 ** 2 - 1, 1.02 * 0.99 - 1, 0.03])
    assert n == 3 and mean == pytest.approx(months.mean()) and sd == pytest.approx(months.std(ddof=1))


@pytest.mark.parametrize("pick", real_picks(), ids=lambda p: p["pick_id"])
def test_expectations_match_a_direct_computation_from_the_trial_file(pick):
    r = pd.read_csv(config.ROOT / pick["backtest_daily_returns_path"], index_col=0, parse_dates=True)["net_ret"]
    n, live = 20, 0.013
    e = compare.expectations(pick, n, live, live_entries=2)
    for tag, series in (("full", r), ("post", r[r.index >= pd.Timestamp(config.REGIMES["post"][0])])):
        v = series.to_numpy()
        rets = [np.prod(1 + v[i:i + n]) - 1 for i in range(len(v) - n + 1)]
        assert e[f"n_windows_{tag}"] == len(rets)
        assert e[f"pct_{tag}"] == pytest.approx(100 * np.mean(np.array(rets) <= live))
    closed = pd.read_csv(config.ROOT / pick["backtest_trades_path"])
    closed = closed[~closed["open_at_end"]]
    assert e["trades_per_month_full"] == pytest.approx(len(closed) / (len(r) / 21))
    assert e["expected_live_trades_full"] == pytest.approx(e["trades_per_month_full"] * n / 21)
