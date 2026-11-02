"""Universe screen (spec section 2) -> research/universe_screen.csv and excluded_pairs.csv."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config
from .trading_calendar import Window


def load_quote_types() -> dict[str, dict]:
    if config.INFO_PATH.exists():
        return json.loads(config.INFO_PATH.read_text())
    return {}


def complete_mask(panel: dict[str, pd.DataFrame], legs: list[str]) -> np.ndarray:
    """True on sessions where every leg has close, adjclose, open and adjopen."""
    ok = np.ones(len(panel["adjclose"]), dtype=bool)
    for t in legs:
        for f in ("close", "adjclose", "open", "adjopen"):
            ok &= panel[f][t].notna().to_numpy()
    return ok


def window_eligibility(mask: np.ndarray, windows: list[Window]) -> list[bool]:
    """A window is tradable if the legs have complete data over the training sample AND the test window."""
    return [bool(mask[w.fit_start:w.test_end].all()) for w in windows]


def first_oos_start(mask: np.ndarray, windows: list[Window], sess: pd.DatetimeIndex):
    for w, ok in zip(windows, window_eligibility(mask, windows)):
        if ok:
            return sess[w.test_start]
    return None


def run_screen(frames, missing, qa_errors: dict[str, str], panel, sess, windows) -> pd.DataFrame:
    info = load_quote_types()
    cands = pd.read_csv(config.CANDIDATES_PATH)
    cand_legs = set(cands.leg_a) | set(cands.leg_b)
    tickers = sorted(cand_legs | set(config.BENCHMARKS))
    rows = []
    for t in tickers:
        role = ("candidate_leg" if t in cand_legs else "") + ("+" if t in cand_legs and t in config.BENCHMARKS else "") \
            + ("benchmark" if t in config.BENCHMARKS else "")
        rec = {"ticker": t, "role": role}
        qt = (info.get(t) or {}).get("quoteType")
        if qt:
            rec["quote_type"], rec["quote_type_source"] = qt, "yfinance.info"
        else:
            rec["quote_type"] = "ETF" if t in config.ETF_FALLBACK else "EQUITY"
            rec["quote_type_source"] = "fallback_hand_list"
        rec["is_etf"] = rec["quote_type"].upper() == "ETF"
        htb = t in config.HTB_FLAGS
        rec["htb_flag"] = htb
        rec["htb_note"] = config.HTB_FLAGS.get(t, "")
        if t not in frames:
            rec.update({"first_date": None, "last_date": None, "rows": 0, "med_dv_252": np.nan, "med_dv_post": np.nan,
                        "liq_pass": False, "first_oos_start": None, "rule_a_eligible": False, "rule_b_eligible": False,
                        "slippage_bps": np.nan, "borrow_rate": np.nan, "data_ok": False,
                        "data_issue": missing.get(t, "no data")})
            rows.append(rec)
            continue
        df = frames[t]
        dv = df["close"] * df["volume"]
        med252 = float(dv.iloc[-252:].median())
        medpost = float(dv[df.index >= pd.Timestamp(config.POST_DV_START)].median())
        mask = complete_mask(panel, [t])
        fos = first_oos_start(mask, windows, sess)
        data_ok = t not in qa_errors
        rec.update({
            "first_date": str(df.index[0].date()), "last_date": str(df.index[-1].date()), "rows": len(df),
            "med_dv_252": med252, "med_dv_post": medpost,
            "liq_pass": bool(med252 > config.LIQUIDITY_MIN_DV and medpost > config.LIQUIDITY_MIN_DV),
            "first_oos_start": str(fos.date()) if fos is not None else None,
            "rule_a_eligible": bool(fos is not None and fos <= config.RULE_A_OOS_BY),
            "rule_b_eligible": bool(fos is not None and fos <= config.RULE_B_OOS_BY),
            "data_ok": bool(data_ok), "data_issue": qa_errors.get(t, ""),
        })
        m = min(med252, medpost)   # conservative: the smaller of the two medians drives the tiers
        big = m >= (100e6 if rec["is_etf"] else 500e6)
        rec["slippage_bps"] = config.SLIPPAGE_BPS_LOW if big else config.SLIPPAGE_BPS_HIGH
        rec["borrow_rate"] = config.BORROW_HTB if (htb or m < 50e6) else config.BORROW_GC
        rows.append(rec)
    cols = ["ticker", "role", "quote_type", "quote_type_source", "is_etf", "first_date", "last_date", "rows",
            "med_dv_252", "med_dv_post", "liq_pass", "first_oos_start", "rule_a_eligible", "rule_b_eligible",
            "htb_flag", "htb_note", "slippage_bps", "borrow_rate", "data_ok", "data_issue"]
    return pd.DataFrame(rows)[cols]


def select_pool(cands: pd.DataFrame, screen: pd.DataFrame, panel, sess, windows):
    """Return (pool, excluded). Excluded pairs carry every reason that applies; `stage` is the first failing one
    (data -> screen)."""
    s = screen.set_index("ticker")
    pool_rows, ex_rows = [], []
    for r in cands.itertuples():
        reasons, stages = [], []
        legs = (("A", r.leg_a), ("B", r.leg_b))
        for side, t in legs:
            if t not in s.index or s.loc[t, "rows"] == 0:
                reasons.append(f"leg {side} {t}: no data on Yahoo ({s.loc[t, 'data_issue'] if t in s.index else 'unknown'})")
                stages.append("data")
            elif not s.loc[t, "data_ok"]:
                reasons.append(f"leg {side} {t}: unresolved data errors [{s.loc[t, 'data_issue']}]")
                stages.append("data")
        for side, t in legs:
            if t in s.index and s.loc[t, "rows"] > 0 and not s.loc[t, "liq_pass"]:
                reasons.append(f"leg {side} {t}: liquidity (median $vol 252d={s.loc[t, 'med_dv_252'] / 1e6:.1f}M, "
                               f"post-COVID={s.loc[t, 'med_dv_post'] / 1e6:.1f}M; need >20M both)")
                stages.append("screen")
        mask = complete_mask(panel, [r.leg_a, r.leg_b]) if all(t in panel["adjclose"].columns for _, t in legs) else None
        fos = first_oos_start(mask, windows, sess) if mask is not None else None
        if mask is not None and (fos is None or fos > config.RULE_B_OOS_BY):
            firsts = {t: s.loc[t, "first_date"] for _, t in legs}
            reasons.append(f"history: first joint OOS window start {fos.date() if fos is not None else 'none'} > "
                           f"{config.RULE_B_OOS_BY.date()} (first dates {firsts})")
            stages.append("screen")
        if reasons:
            ex_rows.append({"pair_id": r.pair_id, "leg_a": r.leg_a, "leg_b": r.leg_b, "type": r.type, "group": r.group,
                            "stage": "data" if "data" in stages else "screen", "reason": " | ".join(reasons)})
        else:
            pool_rows.append({**r._asdict(), "first_oos_start": fos,
                              "rule_a_eligible": bool(fos <= config.RULE_A_OOS_BY)})
    pool = pd.DataFrame(pool_rows).drop(columns=["Index"], errors="ignore")
    ex = pd.DataFrame(ex_rows, columns=["pair_id", "leg_a", "leg_b", "type", "group", "stage", "reason"])
    return pool, ex
