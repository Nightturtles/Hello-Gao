"""Pre-registered constants (research/QUANT_SPEC.md). Do not tune."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST_PATH = DATA_DIR / "MANIFEST.json"
INFO_PATH = DATA_DIR / "ticker_info.json"
RESEARCH_DIR = ROOT / "research"
CANDIDATES_PATH = RESEARCH_DIR / "candidates.csv"
SCREEN_PATH = RESEARCH_DIR / "universe_screen.csv"
RESULTS_DIR = ROOT / "backtest" / "results"
TRIALS_DIR = RESULTS_DIR / "trials"
CHARTS_DIR = ROOT / "backtest" / "charts"

SEED = 20261027

DOWNLOAD_START = "2014-10-01"
DOWNLOAD_END = "2026-10-27"       # yfinance end is exclusive
SNAPSHOT_END = "2026-10-26"       # last complete bar <= this date

BENCHMARKS = ["SPY", "XLE", "GDX", "XME", "GLD", "USO"]

# walk-forward grid (spec section 3)
TRAIN_LEN = 504
TEST_LEN = 63
GRID_START = "2016-10-03"

REGIMES = {
    "pre": ("2016-10-03", "2020-02-28"),
    "covid": ("2020-03-02", "2021-12-31"),
    "post": ("2022-01-03", "2026-10-26"),
    "full": ("2016-10-03", "2026-10-26"),
}
REGIME_ORDER = ["full", "pre", "covid", "post"]

# eligibility cut-offs (spec section 2); evaluated on the walk-forward grid
RULE_A_OOS_BY = pd.Timestamp("2018-10-31")
# 2022-01-03 is the last day of grid window 20; the next grid date (2022-01-04) is the first one
# at/after the post-COVID start, so "can start by 2022-01-03" is evaluated as <= 2022-01-04.
RULE_B_OOS_BY = pd.Timestamp("2022-01-04")

LIQUIDITY_MIN_DV = 20e6
POST_DV_START = "2022-01-03"

# strategy parameters (spec section 5) -- global, never tuned
PARAMS = {
    "z_window": 60,
    "z_entry": 2.0,
    "z_stop": 3.5,
    "z_rearm": 2.0,
    "beta_min": 0.2,
    "beta_max": 5.0,
    "kalman_delta": 1e-4,
    "kalman_ve": 1e-3,
    "kalman_p0": 1e-2,
    "rot_lookback": 20,
    "ll_kmax": 10,
    "ll_tmin": 2.0,
    "ll_zx": 1.0,
}

# engine (spec section 6)
START_CAPITAL = 100_000.0
COMMISSION_PER_SHARE = 0.005
COMMISSION_MIN = 1.0
SLIPPAGE_BPS_LOW = 5.0
SLIPPAGE_BPS_HIGH = 10.0
BORROW_GC = 0.005
BORROW_HTB = 0.03
BORROW_DAYS = 252
# Account-level risk (post-audit engine fix, see research/DECISIONS.md): a margin account is force-liquidated when
# equity falls below the maintenance requirement on the gross position. 25% = FINRA Rule 4210 minimum maintenance.
# Equity <= 0 is ruin: liquidate and stop trading for the rest of the run.
MAINT_MARGIN = 0.25

BOOTSTRAP_MEAN_BLOCK = 20
BOOTSTRAP_RESAMPLES = 2000
N_RANDOM_PAIRS = 500

# gates (spec section 10)
FDR_Q = 0.05

# hard-to-borrow flags taken from the scout notes (research/scouts/*.md)
HTB_FLAGS = {
    "SCCO": "base_metals_steel.md: majority-controlled by Grupo Mexico; borrow thinner than volume suggests",
    "CENX": "base_metals_steel.md: historically high short interest and borrow-fee spikes",
    "ET": "crude_refining.md: MLP borrow can be expensive or tight",
    "EPD": "crude_refining.md: MLP borrow can be expensive or tight",
    "FRO": "crude_refining.md: tanker borrow fees often elevated",
    "DHT": "crude_refining.md: tanker borrow fees often elevated",
    "BNO": "crude_refining.md: borrow may be tighter",
    "GPRE": "agriculture.md: historically elevated short interest",
    "LXU": "natgas_coal_chem.md: elevated short interest; borrow may be tight or costly",
    "AMR": "natgas_coal_chem.md: elevated short interest at times",
    "HCC": "natgas_coal_chem.md: elevated short interest at times",
    "GDXJ": "precious_metals.md: can become hard to borrow at times",
    "SILJ": "precious_metals.md: borrow fee spikes possible",
    "PPLT": "precious_metals.md: borrow may be limited or fee-heavy",
    "PALL": "precious_metals.md: borrow may be limited or fee-heavy",
    "UEC": "transition_metals.md: high short interest, episodic hard-to-borrow periods",
    "MP": "transition_metals.md: high short interest; borrow may be costly or limited",
    "NXE": "transition_metals.md: borrow likely limited",
    "DNN": "transition_metals.md: elevated borrow cost at times",
    "UUUU": "transition_metals.md: elevated borrow cost at times",
}

# fallback ETF list if yfinance .info fails
ETF_FALLBACK = {
    "BNO", "COPX", "CORN", "CPER", "DBA", "GDX", "GDXJ", "GLD", "JETS", "MOO", "OIH", "PALL",
    "PPLT", "SIL", "SILJ", "SLV", "URA", "URNM", "USO", "XOP", "SPY", "XLE", "XME",
}
