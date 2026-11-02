"""Spec 12.6: identical inputs give identical outputs; parallel and serial execution agree; results hash is current."""
import hashlib
import sys

import numpy as np
import pandas as pd
import pytest

from backtest import config, data, runner, strategies, walkforward as wf
from tests import synth


@pytest.mark.parametrize("rule", strategies.RULES)
def test_engine_is_deterministic(rule):
    p = synth.leadlag(2) if rule.startswith("leadlag") else synth.cointegrated(2, half_life=6, stat_sd=0.08)
    a = wf.run_pair_rule(rule, p, synth.WINDOWS)
    b = wf.run_pair_rule(rule, p, synth.WINDOWS)
    pd.testing.assert_frame_equal(a.daily, b.daily, check_exact=True)
    pd.testing.assert_frame_equal(a.trades, b.trades, check_exact=True)
    assert a.final_state == b.final_state and a.final_fit == b.final_fit


def test_serial_and_parallel_task_runs_agree(tmp_path):
    pairs = [synth.cointegrated(1), synth.independent(3), synth.leadlag(4)]
    panel, screen = synth.panel_from_pairs(pairs)
    spy = panel["adjclose"]["SPY"].pct_change()
    runner.set_context(panel, screen, synth.WINDOWS, spy, 2530, tmp_path)
    tasks = []
    for i in range(3):
        for rule in ("coint_ols", "coint_kalman", "rotation", "leadlag"):
            tasks.append({"idx": len(tasks), "pair_id": f"P{i}", "leg_a": f"S{i}A", "leg_b": f"S{i}B", "rule": rule,
                          "save": True, "bootstrap": True})
    r1 = runner.run_tasks(tasks, processes=1)
    r2 = runner.run_tasks(tasks, processes=3)
    assert len(r1) == len(r2) == 12
    for (m1, w1), (m2, w2) in zip(r1, r2):
        assert m1.keys() == m2.keys()
        for k in m1:
            v1, v2 = m1[k], m2[k]
            if isinstance(v1, float) and np.isnan(v1):
                assert np.isnan(v2), k
            else:
                assert v1 == v2, k
        assert w1 == w2 or pd.DataFrame(w1).equals(pd.DataFrame(w2))
    assert (tmp_path / "P0__coint_ols.csv.gz").exists() and (tmp_path / "P0__coint_ols_trades.csv").exists()


def test_leadlag_engine_hold_is_k_sessions():
    p = synth.leadlag(21, lag=4, strength=0.9)
    res = wf.run_pair_rule("leadlag", p, synth.WINDOWS)
    closed = res.trades[~res.trades.open_at_end]
    assert len(closed) > 50
    ks = res.windows.set_index("test_start")["k_star"]
    assert set(closed["holding_days"]) == {4}


def test_research_code_never_needs_the_network(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", None)      # any `import yfinance` now raises ImportError
    frames, missing = data.load_all(["SPY", "GLD"])
    assert not missing and set(frames) == {"SPY", "GLD"}
    from backtest.trading_calendar import sessions, walk_forward_grid
    sess = sessions()
    qa = data.run_qa(frames, missing, sess, walk_forward_grid(sess))
    assert len(qa) > 0


def test_cache_matches_manifest():
    assert data.verify_manifest() == []


def test_results_hash_file_matches_gates_csv_if_present():
    gates = config.RESULTS_DIR / "gates.csv"
    h = config.RESULTS_DIR / "RESULTS_HASH.txt"
    if not (gates.exists() and h.exists()):
        pytest.skip("run `python -m backtest.run_all` first")
    assert hashlib.sha256(gates.read_bytes()).hexdigest() in h.read_text()
