"""Parallel execution of (pair, rule) runs.  Each task is independent and seeded from its task index, so results
do not depend on the number of processes or on scheduling order."""
from __future__ import annotations

import multiprocessing as mp
import os

import numpy as np
import pandas as pd

from . import config, metrics, walkforward

_CTX: dict = {}


def set_context(panel, screen, windows, spy_ret, full_days, trials_dir=None) -> None:
    _CTX.update(panel=panel, screen=screen, windows=windows, spy_ret=spy_ret, full_days=full_days,
                trials_dir=trials_dir)


def task_key(pair_id: str, rule: str) -> str:
    return f"{pair_id}__{rule}"


def _run_task(task: dict):
    """task: idx, pair_id, leg_a, leg_b, rule, save(bool), bootstrap(bool)."""
    pdat = walkforward.build_pair_data(_CTX["panel"], _CTX["screen"], task["pair_id"], task["leg_a"], task["leg_b"])
    res = walkforward.run_pair_rule(task["rule"], pdat, _CTX["windows"])
    rng = np.random.default_rng([config.SEED, int(task["idx"])]) if task["bootstrap"] else None
    m = metrics.compute_metrics(res.daily, res.trades, _CTX["spy_ret"], res.meta["covered_days"], _CTX["full_days"],
                                rng=rng, bootstrap=task["bootstrap"])
    m.update({"pair_id": task["pair_id"], "leg_a": task["leg_a"], "leg_b": task["leg_b"], "rule": task["rule"],
              "stopped": res.meta["stopped"], "n_windows": res.meta["n_windows"],
              "n_windows_valid": int(res.windows["valid"].sum()) if len(res.windows) else 0})
    if task["save"]:
        d = _CTX["trials_dir"]
        k = task_key(task["pair_id"], task["rule"])
        res.daily.to_csv(d / f"{k}.csv.gz", float_format="%.10g", compression={"method": "gzip", "mtime": 0})
        res.trades.to_csv(d / f"{k}_trades.csv", float_format="%.10g", index=False)
    wl = res.windows.to_dict("records") if task["save"] else []
    return m, wl


def run_tasks(tasks: list[dict], processes: int | None = None):
    processes = processes or max(1, (os.cpu_count() or 1))
    if processes == 1 or len(tasks) < 4:
        return [_run_task(t) for t in tasks]
    ctx = mp.get_context("fork")
    with ctx.Pool(processes) as pool:
        return pool.map(_run_task, tasks, chunksize=4)
