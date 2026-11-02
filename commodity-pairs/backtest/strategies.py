"""Trading rules (spec section 5).  Shared, unchanged, by the backtest and the live paper-trading simulator.

Interface
---------
``fit(rule, hist_A, hist_B, params) -> FitResult``
    Called once per walk-forward window with the TRAINING adjusted closes only (strictly before the
    window's first test day).

``initial_state(rule) -> dict`` / ``new_window_state(rule, prev_state, fit, params) -> dict``
    The per-pair state is a plain JSON-serialisable dict.  ``new_window_state`` is called right after
    ``fit`` at each window start; it keeps any open trade and re-bases the rule's online estimators on
    the new fit.

``step(rule, state, hist_A, hist_B, fit, params) -> (new_state, target, reason)``
    Called exactly ONCE per trading day, after the close, in date order.  ``hist_A`` / ``hist_B`` are
    1-D arrays of ADJUSTED CLOSES up to and including today (only the trailing ``z_window + 1`` values
    are needed; the backtest passes zero-copy views).  ``target`` is ``{"A": w_A, "B": w_B}``, signed
    weights as a fraction of equity (gross = 1.0 in a trade, 0 when flat).  ``reason`` is a
    human-readable string.  The caller fills the target at the NEXT open.

Rules: ``coint_ols``, ``coint_kalman``, ``rotation``, ``leadlag`` (leader = A, follower = B) and
``leadlag_rev`` (leader = B, follower = A).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

RULES = ("coint_ols", "coint_kalman", "rotation", "leadlag", "leadlag_rev")

# Which primary p-value a rule is allowed to pass on (spec 5, "type consistency").
RULE_P_TYPE = {
    "coint_ols": "eg",
    "coint_kalman": "eg",
    "rotation": "inverse",
    "leadlag": "granger_ab",
    "leadlag_rev": "granger_ba",
}

FLAT = {"A": 0.0, "B": 0.0}


# --------------------------------------------------------------------------- fit result
@dataclass
class FitResult:
    rule: str
    valid: bool = True            # False -> no new entries this window
    reason: str = ""
    n_train: int = 0
    alpha: float | None = None    # OLS intercept
    beta: float | None = None     # OLS hedge ratio (coint_ols)
    k: int | None = None          # lead-lag horizon k*
    slope: float | None = None    # b*
    tstat: float | None = None
    sigma_L: float | None = None
    h: float | None = None
    kalman: dict | None = None    # filter state at the end of the training sample
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FitResult":
        return cls(**d)


def _f(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


# --------------------------------------------------------------------------- helpers
def _ols(y: np.ndarray, x: np.ndarray):
    """OLS y = a + b x.  Returns (a, b, tstat_b)."""
    n = len(x)
    xm, ym = x.mean(), y.mean()
    dx = x - xm
    sxx = float(dx @ dx)
    if sxx <= 0 or n < 3:
        return ym, float("nan"), float("nan")
    b = float(dx @ (y - ym)) / sxx
    a = ym - b * xm
    resid = y - a - b * x
    s2 = float(resid @ resid) / (n - 2)
    se = math.sqrt(s2 / sxx) if s2 > 0 else float("nan")
    return float(a), b, (b / se if se and se > 0 else float("nan"))


def _zscore(s: np.ndarray) -> float:
    sd = float(s.std(ddof=1))
    if not math.isfinite(sd) or sd <= 1e-14:
        return float("nan")
    return float((s[-1] - s.mean()) / sd)


def _tail(h, n: int) -> np.ndarray:
    return np.asarray(h, dtype=float)[-n:]


def _weights(direction: int, beta: float) -> list[float]:
    """Spread weights: direction +1 = long spread (long A, short B)."""
    return [direction / (1.0 + beta), -direction * beta / (1.0 + beta)]


# --------------------------------------------------------------------------- Kalman filter
def kalman_init_state(theta0, p0: float) -> dict:
    return {"a": float(theta0[0]), "b": float(theta0[1]), "p00": float(p0), "p01": 0.0, "p11": float(p0), "buf": []}


def kalman_update(kf: dict, ly: float, lx: float, delta: float, ve: float) -> float:
    """Advance the filter by one observation.  Returns the innovation e_t = ly - (a_{t-1} + b_{t-1} lx),
    i.e. the spread computed from the PREVIOUS day's state (strictly causal).  `kf` is mutated."""
    w = delta / (1.0 - delta)
    a, b = kf["a"], kf["b"]
    p00, p01, p11 = kf["p00"] + w, kf["p01"], kf["p11"] + w     # predict: P + W
    e = ly - (a + b * lx)
    q = p00 + 2.0 * p01 * lx + p11 * lx * lx + ve
    xp0 = p00 + lx * p01
    xp1 = p01 + lx * p11
    k0, k1 = xp0 / q, xp1 / q
    kf["a"], kf["b"] = a + k0 * e, b + k1 * e
    kf["p00"], kf["p01"], kf["p11"] = p00 - k0 * xp0, p01 - k0 * xp1, p11 - k1 * xp1
    return e


def kalman_path(ly: np.ndarray, lx: np.ndarray, params: dict, n_init: int = 504):
    """Run the filter over a whole log-price history (for the stats report).  Initialised by OLS on the first
    `n_init` observations.  Returns arrays (alpha_{t-1}, beta_{t-1}) aligned so that entry t holds the state used
    to form the spread at t, plus the innovations."""
    n0 = min(n_init, len(ly))
    a, b, _ = _ols(ly[:n0], lx[:n0])
    kf = kalman_init_state((a, b), params["kalman_p0"])
    al, be, inn = np.empty(len(ly)), np.empty(len(ly)), np.empty(len(ly))
    for t in range(len(ly)):
        al[t], be[t] = kf["a"], kf["b"]
        inn[t] = kalman_update(kf, float(ly[t]), float(lx[t]), params["kalman_delta"], params["kalman_ve"])
    return al, be, inn


# --------------------------------------------------------------------------- fit
def fit(rule: str, hist_A, hist_B, params: dict) -> FitResult:
    if rule not in RULES:
        raise ValueError(f"unknown rule {rule}")
    A = np.asarray(hist_A, dtype=float)
    B = np.asarray(hist_B, dtype=float)
    n = len(A)
    if n != len(B):
        raise ValueError("training histories must have equal length")
    fr = FitResult(rule=rule, n_train=n)
    if rule == "rotation":
        return fr
    if not (np.isfinite(A).all() and np.isfinite(B).all() and (A > 0).all() and (B > 0).all()):
        fr.valid, fr.reason = False, "training data incomplete"
        return fr
    la, lb = np.log(A), np.log(B)
    if rule in ("coint_ols", "coint_kalman"):
        alpha, beta, _ = _ols(la, lb)
        fr.alpha, fr.beta = _f(alpha), _f(beta)
        if rule == "coint_ols":
            if fr.beta is None or fr.beta <= params["beta_min"] or fr.beta > params["beta_max"]:
                fr.valid, fr.reason = False, "beta out of range"
            return fr
        # Kalman: initialise on OLS of the training sample, then run the filter through the training data
        kf = kalman_init_state((alpha, beta), params["kalman_p0"])
        buf: list[float] = []
        w = params["z_window"]
        for t in range(n):
            e = kalman_update(kf, float(la[t]), float(lb[t]), params["kalman_delta"], params["kalman_ve"])
            buf.append(e)
            if len(buf) > w:
                buf.pop(0)
        kf["buf"] = [float(v) for v in buf]
        fr.kalman = {k: (v if k == "buf" else float(v)) for k, v in kf.items()}
        fr.beta = _f(kf["b"])
        return fr
    # lead-lag
    if rule == "leadlag":
        lL, lF = la, lb
    else:
        lL, lF = lb, la
    best = None
    for k in range(1, params["ll_kmax"] + 1):
        if n - 2 * k < 10:
            break
        x = lL[k:n - k] - lL[:n - 2 * k]
        y = lF[2 * k:n] - lF[k:n - k]
        _, b, t = _ols(y, x)
        if math.isfinite(t) and (best is None or abs(t) > abs(best[2])):
            best = (k, b, t)
    if best is None:
        fr.valid, fr.reason = False, "lead-lag regression failed"
        return fr
    k, b, t = best
    rL, rF = np.diff(lL), np.diff(lF)
    _, h, _ = _ols(rF, rL)
    fr.k, fr.slope, fr.tstat = int(k), _f(b), _f(t)
    fr.sigma_L, fr.h = _f(rL.std(ddof=1)), _f(h)
    if fr.tstat is None or abs(fr.tstat) < params["ll_tmin"]:
        fr.valid, fr.reason = False, "lead-lag |t| < 2"
    elif fr.h is None or fr.h <= 0 or fr.sigma_L is None or fr.sigma_L <= 0:
        fr.valid, fr.reason = False, "lead-lag hedge ratio h <= 0"
    return fr


# --------------------------------------------------------------------------- state
def initial_state(rule: str) -> dict:
    return {
        "pos": 0,               # +1/-1 position code (0 = flat)
        "armed": True,
        "w": [0.0, 0.0],        # frozen target weights while in a trade
        "beta_entry": None,
        "days_held": 0,
        "k_entry": None,
        "z": None,              # last z-score / signal value (for logging and charts)
        "spread": None,
        "beta_used": None,
        "kalman": None,
    }


def new_window_state(rule: str, prev: dict | None, fit_: FitResult, params: dict) -> dict:
    """Start a new window: keep any open trade, re-base online estimators on the new fit."""
    st = dict(prev) if prev else initial_state(rule)
    if rule == "coint_kalman":
        if fit_.kalman is not None:
            st["kalman"] = {k: (list(v) if k == "buf" else float(v)) for k, v in fit_.kalman.items()}
        else:
            st["kalman"] = None
    return st


# --------------------------------------------------------------------------- step
def _step_coint(rule: str, st: dict, hA, hB, fit_: FitResult, p: dict):
    W = p["z_window"]
    la, lb = np.log(_tail(hA, W)), np.log(_tail(hB, W))
    kalman = rule == "coint_kalman"
    if kalman:
        kf = dict(st["kalman"]) if st.get("kalman") else None
        if kf is None:
            st["z"], st["spread"], st["beta_used"] = None, None, None
            return st, dict(FLAT), "no kalman state"
        beta_prev = kf["b"]
        e = kalman_update(kf, float(la[-1]), float(lb[-1]), p["kalman_delta"], p["kalman_ve"])
        buf = list(kf["buf"])
        buf.append(e)
        if len(buf) > W:
            buf = buf[-W:]
        kf["buf"] = buf
        st["kalman"] = kf
        z = _zscore(np.asarray(buf)) if len(buf) >= W else float("nan")
        st["spread"], st["beta_used"] = float(e), float(beta_prev)
    pos = st["pos"]
    if pos != 0:
        if not kalman:
            beta = st["beta_entry"]
            s = la - beta * lb
            z = _zscore(s)
            st["spread"], st["beta_used"] = float(s[-1]), float(beta)
        st["z"] = _f(z)
        if not math.isfinite(z):
            return st, {"A": st["w"][0], "B": st["w"][1]}, "hold (z undefined)"
        if abs(z) >= p["z_stop"]:
            st.update(pos=0, armed=False, w=[0.0, 0.0], beta_entry=None)
            return st, dict(FLAT), f"stop exit |z|={abs(z):.2f}>={p['z_stop']}"
        if (pos == 1 and z >= 0.0) or (pos == -1 and z <= 0.0):
            st.update(pos=0, w=[0.0, 0.0], beta_entry=None)
            return st, dict(FLAT), f"exit z={z:.2f} crossed 0"
        return st, {"A": st["w"][0], "B": st["w"][1]}, f"hold {'long' if pos == 1 else 'short'} spread z={z:.2f}"
    # ---- flat
    if not kalman:
        if not fit_.valid:
            st["z"], st["spread"], st["beta_used"] = None, None, None
            return st, dict(FLAT), fit_.reason or "no entries this window"
        beta = fit_.beta
        s = la - beta * lb
        z = _zscore(s)
        st["spread"], st["beta_used"] = float(s[-1]), float(beta)
    else:
        beta = beta_prev
    st["z"] = _f(z)
    if not math.isfinite(z):
        return st, dict(FLAT), "z undefined"
    if not st["armed"]:
        if abs(z) < p["z_rearm"]:
            st["armed"] = True
            return st, dict(FLAT), f"re-armed |z|={abs(z):.2f}"
        return st, dict(FLAT), f"disarmed |z|={abs(z):.2f}"
    if z <= -p["z_entry"] or z >= p["z_entry"]:
        if not (p["beta_min"] < beta <= p["beta_max"]):
            return st, dict(FLAT), "beta out of range"
        d = 1 if z <= -p["z_entry"] else -1
        w = _weights(d, beta)
        st.update(pos=d, w=w, beta_entry=float(beta), days_held=0)
        return st, {"A": w[0], "B": w[1]}, f"entry {'long' if d == 1 else 'short'} spread z={z:.2f}"
    return st, dict(FLAT), f"flat z={z:.2f}"


def _step_rotation(st: dict, hA, hB, p: dict):
    L = p["rot_lookback"]
    a, b = _tail(hA, L + 1), _tail(hB, L + 1)
    if len(a) < L + 1:
        return st, dict(FLAT), "insufficient history"
    ra, rb = a[-1] / a[0] - 1.0, b[-1] / b[0] - 1.0
    if not (math.isfinite(ra) and math.isfinite(rb)):
        return st, ({"A": st["w"][0], "B": st["w"][1]}), "nan return, hold"
    st["z"] = float(ra - rb)
    new = 1 if ra > rb else -1
    old = st["pos"]
    st["pos"] = new
    st["w"] = [0.5 * new, -0.5 * new]
    tgt = {"A": 0.5 * new, "B": -0.5 * new}
    if old == 0:
        return st, tgt, f"open {'long A / short B' if new == 1 else 'short A / long B'} (R_A-R_B={ra - rb:+.3f})"
    if new != old:
        return st, tgt, f"flip to {'long A / short B' if new == 1 else 'short A / long B'} (R_A-R_B={ra - rb:+.3f})"
    return st, tgt, "hold"


def _step_leadlag(rule: str, st: dict, hA, hB, fit_: FitResult, p: dict):
    pos = st["pos"]
    if pos != 0:
        st["days_held"] += 1
        if st["days_held"] >= st["k_entry"]:
            st.update(pos=0, w=[0.0, 0.0])
            return st, dict(FLAT), f"exit after {st['k_entry']}d hold"
        return st, {"A": st["w"][0], "B": st["w"][1]}, f"hold day {st['days_held']}/{st['k_entry']}"
    if not fit_.valid:
        st["z"], st["spread"], st["beta_used"] = None, None, None
        return st, dict(FLAT), fit_.reason or "no entries this window"
    k = fit_.k
    hL, hF = (hA, hB) if rule == "leadlag" else (hB, hA)
    L = np.log(_tail(hL, k + 1))
    if len(L) < k + 1:
        return st, dict(FLAT), "insufficient history"
    x = float(L[-1] - L[0])
    zx = x / (fit_.sigma_L * math.sqrt(k))
    st["z"] = _f(zx)
    st["beta_used"] = fit_.h
    if not math.isfinite(zx) or abs(zx) < p["ll_zx"]:
        return st, dict(FLAT), f"flat z_x={zx:.2f}"
    d = 1 if fit_.slope * x > 0 else -1
    h = fit_.h
    wF, wL = d / (1.0 + h), -d * h / (1.0 + h)
    w = [wL, wF] if rule == "leadlag" else [wF, wL]
    st.update(pos=d, w=w, days_held=0, k_entry=int(k), beta_entry=float(h))
    return st, {"A": w[0], "B": w[1]}, f"entry {'long' if d == 1 else 'short'} follower z_x={zx:.2f} k={k}"


def force_flat(rule: str, state: dict) -> dict:
    """Account-level forced liquidation (margin call or ruin), applied by the caller after ``step``.  The rule goes
    flat; spread rules also disarm, exactly as after a stop, so they re-arm only once |z| < z_rearm."""
    st = dict(state)
    st.update(pos=0, w=[0.0, 0.0], beta_entry=None, days_held=0, k_entry=None)
    if rule in ("coint_ols", "coint_kalman"):
        st["armed"] = False
    return st


def step(rule: str, state: dict, hist_A, hist_B, fit_: FitResult, params: dict):
    """Advance one day.  Returns (new_state, target, reason).  `state` is not mutated."""
    st = dict(state)
    if rule in ("coint_ols", "coint_kalman"):
        return _step_coint(rule, st, hist_A, hist_B, fit_, params)
    if rule == "rotation":
        return _step_rotation(st, hist_A, hist_B, params)
    if rule in ("leadlag", "leadlag_rev"):
        return _step_leadlag(rule, st, hist_A, hist_B, fit_, params)
    raise ValueError(f"unknown rule {rule}")
